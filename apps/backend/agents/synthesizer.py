import os
import re
import torch
import torchaudio
from TTS.api import TTS
from pathlib import Path
from config import TEMP_DIR

# Fix architetturale: Forza torchaudio a utilizzare il backend 'soundfile' in Python 3.12 
# per prevenire problemi di compatibilità ed evitare fallimenti con driver sperimentali.
try:
    if "soundfile" in torchaudio.list_audio_backends():
        torchaudio.set_audio_backend("soundfile")
except Exception:
    # Fallback per le versioni più recenti dove set_audio_backend potrebbe essere deprecato
    pass


class SynthesizerAgent:
    """
    Agente per la sintesi vocale (Text-to-Speech).
    Implementa una gestione avanzata della memoria RAM e il partizionamento del testo (chunking)
    al fine di prevenire il fenomeno dell'Attention Collapse nel modello XTTS_v2.
    """
    def __init__(self, model_name: str="tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Inizializza il motore TTS preaddestrato.
        """
        os.environ["COQUI_TOS_AGREED"] = "1"  # Accetta in automatico la licenza CPML
        # Legge la variabile d'ambiente USE_CUDA. Se è 'true', usa la GPU. Altrimenti CPU.
        use_cuda_env = os.environ.get("USE_CUDA", "false").lower() == "true"
        use_gpu = use_cuda_env and torch.cuda.is_available()
        if use_cuda_env and not use_gpu:
            print("[WARNING] È stato richiesto USE_CUDA=true, ma PyTorch non rileva una GPU compatibile. Fallback su CPU.")
        # Inizializza il modello limitando l'elaborazione ad un solo thread/CPU per evitare regressioni
        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=use_gpu)
    
    def _chunk_text(self, text: str, max_chars: int = 200) -> list[str]:
        """
        Segmenta una stringa di testo in frammenti (chunk) rispettando una lunghezza massima predefinita.
        Preserva i punti critici di punteggiatura per mantenere la prosodia naturale durante la sintesi.
        """
        # Divide il testo utilizzando un'espressione regolare mirata alla punteggiatura terminale (punti finali, esclamativi e interrogativi)
        sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # Logica di fallback: elaborazione stringhe eccezionalmente lunghe che non superano la soglia di troncamento standard preimpostato
                if len(sentence) >= max_chars:
                    words = sentence.split(' ')
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) < max_chars:
                            temp_chunk += word + " "
                        else:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word + " "
                    current_chunk = temp_chunk
                else:
                    current_chunk = sentence + " "
                    
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks

    def generate_audio(self, text: str, target_language: str, reference_audio_path: str) -> str:
        """
        Produce un campionamento vocale clonando i timbri dal file audio sorgente per generare
        nuovo contenuto parlato nella lingua e dal testo di input stabiliti.
        """
        try:
            output_filename = f"dubbed_{target_language}.wav"
            output_path = str(TEMP_DIR / output_filename)
            
            # 1. Segmentazione formale del testo in partizioni stabili pre-elaborative (limitazione del carico LLM)
            chunks = self._chunk_text(text)
            audio_tensors = []
            
            # 2. Generazione iterativa della forma d'onda acustica salvando ogni segmento virtuale in RAM
            for chunk in chunks:
                if not chunk.strip(): 
                    continue
                # Il metodo core tts.tts produce un array sequenziale di elementi floating-point rappresentante il flusso audio nativo
                wav_array = self.tts.tts(
                    text=chunk, 
                    speaker_wav=reference_audio_path, 
                    language=target_language
                )
                audio_tensors.append(torch.tensor(wav_array))
            
            if not audio_tensors:
                raise ValueError("Eccezione di generazione: Nessun frammento di testo valido individuabile in post-segmentazione.")
                
            # 3. Concatenazione tensoriale (fusione sull'asse primario) con dimensionamento di un singolo canale stereo compatibile [1, sample_frames]
            final_audio = torch.cat(audio_tensors).unsqueeze(0)
            
            # 4. Scrittura finale bufferizzata sul disco fisso (frequenza di campionamento fissa del modello XTTS_v2 equivalente a 24.000 Hz)
            torchaudio.save(output_path, final_audio, 24000)
            
            return output_path
            
        except Exception as e:
            return f"[ERRORE DI SINTESI VOCALE]: {str(e)}"