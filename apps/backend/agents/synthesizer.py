import os
import re
import torch
import torchaudio
from TTS.api import TTS
from pathlib import Path
from config import TEMP_DIR

# Forza torchaudio a utilizzare il backend 'soundfile' in Python 3.12+ 
# per evitare bug di compatibilità.
try:
    if "soundfile" in torchaudio.list_audio_backends():
        torchaudio.set_audio_backend("soundfile")
except Exception:
    # Fallback per versioni in cui set_audio_backend è deprecato
    pass


class SynthesizerAgent:
    """
    Agente per la sintesi vocale (TTS).
    Implementa il chunking del testo per prevenire l'attention collapse nel modello XTTS_v2.
    """
    def __init__(self, model_name: str="tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Inizializza il motore TTS.
        """
        os.environ["COQUI_TOS_AGREED"] = "1"  # Accetta la licenza CPML per evitare blocchi interattivi
        
        # Gestione hardware: verifica CUDA ed esegue il fallback su CPU se necessario
        use_cuda_env = os.environ.get("USE_CUDA", "false").lower() == "true"
        use_gpu = use_cuda_env and torch.cuda.is_available()
        
        if use_cuda_env and not use_gpu:
            print("[AVVISO] CUDA richiesta ma non disponibile. Fallback su CPU in corso.")
            
        # Inizializza il modello TTS
        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=use_gpu)
    
    def _chunk_text(self, text: str, max_chars: int = 200) -> list[str]:
        """
        Divide il testo in chunk di lunghezza massima `max_chars`.
        Preserva la punteggiatura per mantenere una prosodia naturale.
        """
        # Split sulla punteggiatura finale per preservare le frasi
        sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # Fallback per frasi più lunghe di max_chars: divide per parole
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

    def generate_audio(self, text, target_language, reference_audio_path, progress_callback=None):
        """
        Genera l'audio TTS clonando la voce dal file di riferimento,
        nella lingua e col testo specificati.
        """
        try:
            output_filename = f"dubbed_{target_language}.wav"
            output_path = str(TEMP_DIR / output_filename)
            
            # 1. Chunking del testo
            chunks = self._chunk_text(text)
            audio_tensors = []
            
            # 2. Sintesi audio per ogni chunk
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    current_pct = int ((i/len(chunks)) * 100)
                    progress_callback(current_pct, "synthesizing")
                if not chunk.strip(): 
                    continue
                # Generazione dell'array audio
                wav_array = self.tts.tts(
                    text=chunk, 
                    speaker_wav=reference_audio_path, 
                    language=target_language
                )
                audio_tensors.append(torch.tensor(wav_array))
            
            if not audio_tensors:
                raise ValueError("Nessun chunk di testo valido da sintetizzare.")
                
            # 3. Concatenazione dei tensori audio
            final_audio = torch.cat(audio_tensors).unsqueeze(0)
            
            # 4. Salvataggio del file su disco (frequenza di campionamento XTTS_v2: 24kHz)
            torchaudio.save(output_path, final_audio, 24000)
            
            return output_path
            
        except Exception as e:
            return f"[ERRORE DI SINTESI VOCALE]: {str(e)}"