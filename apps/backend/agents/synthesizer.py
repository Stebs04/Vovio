# Importa il modulo os per interfacciarsi con il sistema operativo, ad esempio per leggere/impostare variabili d'ambiente.
import os
# Importa le espressioni regolari per manipolazioni testuali avanzate, utili nel chunking del testo.
import re
# Importa la libreria principale PyTorch necessaria per il machine learning e la manipolazione dei tensori.
import torch
# Importa torchaudio per le operazioni di I/O e processamento dei file audio.
import torchaudio
# Dalla libreria TTS di Coqui, importa la classe principale TTS per usare i modelli di sintesi vocale.
from TTS.api import TTS
# Importa Path da pathlib per manipolare i percorsi dei file in modo indipendente dal sistema operativo.
from pathlib import Path
# Importa la directory temporanea dalle configurazioni dell'applicazione per salvare gli output.
from config import TEMP_DIR

# Blocco try-except per gestire la configurazione del backend audio di torchaudio.
# Nelle versioni Python 3.12+ forziamo l'uso di 'soundfile' per evitare bug di compatibilità.
try:
    # Controlla se 'soundfile' è disponibile tra i backend di torchaudio.
    if "soundfile" in torchaudio.list_audio_backends():
        # Imposta esplicitamente il backend audio su 'soundfile'.
        torchaudio.set_audio_backend("soundfile")
except Exception:
    # In caso di eccezione (es. in versioni in cui set_audio_backend è deprecato), passa oltre senza interruzioni.
    pass


# Definizione della classe principale SynthesizerAgent che gestisce la logica di Text-To-Speech.
class SynthesizerAgent:
    """
    Agente per la sintesi vocale (TTS).
    Implementa logiche come il chunking del testo per prevenire l'attention collapse nel modello XTTS_v2,
    garantendo una generazione audio più stabile su testi lunghi.
    """
    
    # Metodo costruttore dell'agente, accetta il nome del modello come parametro opzionale.
    def __init__(self, model_name: str="tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Inizializza il motore TTS configurando le variabili necessarie e caricando il modello.
        """
        # Imposta la variabile d'ambiente per accettare automaticamente i "Terms of Service" di Coqui ed evitare prompt bloccanti a terminale.
        os.environ["COQUI_TOS_AGREED"] = "1"  
        
        # Gestione dell'accelerazione hardware: legge l'intenzione di usare CUDA dalle variabili d'ambiente.
        use_cuda_env = os.environ.get("USE_CUDA", "false").lower() == "true"
        # Verifica se l'uso di CUDA è stato richiesto e se la GPU è effettivamente disponibile sul sistema.
        use_gpu = use_cuda_env and torch.cuda.is_available()
        
        # Se era stata richiesta CUDA ma non è disponibile, avvisa l'utente tramite standard output.
        if use_cuda_env and not use_gpu:
            print("[AVVISO] CUDA richiesta ma non disponibile. Fallback su CPU in corso.")
            
        # Inizializza l'istanza principale del TTS caricando i pesi del modello; disabilita la barra di caricamento e setta il flag gpu.
        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=use_gpu)
    
    # Metodo privato per dividere il testo in blocchi più piccoli per un'elaborazione ottimale da parte del modello TTS.
    def _chunk_text(self, text: str, max_chars: int = 200) -> list[str]:
        """
        Divide il testo in chunk di lunghezza massima `max_chars`.
        Cerca di spezzare sulle frasi intere (usando la punteggiatura) per mantenere una prosodia naturale.
        """
        # Appiattisce i ritorni a capo convertendoli in spazi e compie lo split del testo dopo punti, esclamativi o interrogativi.
        sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
        # Lista che conterrà i chunk elaborati finali.
        chunks = []
        # Accumulatore temporaneo per comporre un chunk finché non si raggiunge la soglia `max_chars`.
        current_chunk = ""
        
        # Itera su ciascuna frase isolata.
        for sentence in sentences:
            # Se l'aggiunta della nuova frase al chunk attuale non supera il limite di caratteri...
            if len(current_chunk) + len(sentence) < max_chars:
                # ...aggiungi la frase e uno spazio.
                current_chunk += sentence + " "
            # Altrimenti (la frase farebbe sforare il limite)...
            else:
                # Se il chunk attuale contiene già testo valido, aggiungilo alla lista finale.
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    
                # Se la singola frase è intrinsecamente più lunga della soglia massima consentita, occorre spezzare parola per parola.
                if len(sentence) >= max_chars:
                    # Divido la frase ultra-lunga in singole parole in base agli spazi.
                    words = sentence.split(' ')
                    # Inizializza un nuovo accumulatore per spezzettare la frase.
                    temp_chunk = ""
                    # Itera sulle parole estratte.
                    for word in words:
                        # Se aggiungere la parola nel temp_chunk non viola il limite max_chars...
                        if len(temp_chunk) + len(word) < max_chars:
                            # ...aggiungi la parola.
                            temp_chunk += word + " "
                        # Altrimenti, quando il temp_chunk è pieno...
                        else:
                            # ...salvalo nella lista dei chunk.
                            chunks.append(temp_chunk.strip())
                            # Inizia un nuovo temp_chunk con la parola attuale.
                            temp_chunk = word + " "
                    # Alla fine del loop, ciò che resta finisce in current_chunk per un'eventuale successiva concatenazione.
                    current_chunk = temp_chunk
                # Se la frase non era lunghissima da sola, essa diventa semplicemente l'inizio del prossimo chunk.
                else:
                    current_chunk = sentence + " "
                        
        # Una volta processate tutte le frasi, se è rimasto qualcosa nel current_chunk, si svuota e si appende in lista.
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
                
        # Restituisce l'array dei chunk testuali validati.
        return chunks
    
    def generate_audio(self, segments: list[dict], target_language: str, reference_audio_path: str, progress_callback=None):
        """
        Sintetizza i frammenti vocali e li posiziona in modo assoluto su una timeline audio.
        Implementa chunking testuale interno per evitare saturazione del modello TTS.
        
        Args:
            segments (list[dict]): Array di payload testuali con i relativi timestamp (start/end).
            target_language (str): Locale di destinazione (es. 'it', 'en').
            reference_audio_path (str): Percorso del file audio target per il features cloning (speaker wav).
            progress_callback (Callable): Hook opzionale per la notifica asincrona dello stato di avanzamento.
            
        Returns:
            str: Il percorso assoluto su filesystem del file audio locale (WAV) generato, o stringa d'errore.
        """
        try:
            # Determinazione del path temporaneo per il salvataggio della traccia vocale isolata.
            output_filename = f"dubbed_{target_language}.wav"
            output_path = str(TEMP_DIR / output_filename)
            
            # Frequenza fissa di campionamento richiesta dai tensori in output del modello XTTS_v2.
            SAMPLE_RATE = 24000 
            
            # Buffer tridimensionale (start, end, tensor). Accumula the clip prima del mix-down finale sulla timeline.
            generated_clips = []
            
            # High-water mark per stabilire l'ampiezza logica del canvas audio preallocato (in campioni).
            max_sample_needed = 0
            
            for i, segment in enumerate(segments):
                # Dispatch dell'evento di status per tracciare il batch upstream sull'interfaccia.
                if progress_callback:
                    current_pct = int((i / len(segments)) * 100)
                    progress_callback(current_pct, "synthesizing")
                
                text_chunk = segment.get('text', '')
                start_time = segment.get('start', 0.0)
                
                # Pruning logico veloce per bypassare frammenti puramente silenziosi o parsati a vuoto.
                if not text_chunk.strip(): 
                    continue
                
                # Split testuale preventivo (chunking). XTTS degrada le performances con testi stringenti 
                # causando instabilità fonetiche a causa del collasso della attention window.
                sub_chunks = self._chunk_text(text_chunk, max_chars=200)
                
                # Mappatura del punto di offset: dal dominio del tempo (secondi) al dominio del campione (discreto).
                current_start_sample = int(start_time * SAMPLE_RATE)
                
                for sub_text in sub_chunks:
                    # Invocazione zero-shot text-to-speech per l'approssimazione vocale (cloning) del blocco.
                    wav_array = self.tts.tts(
                        text=sub_text, 
                        speaker_wav=reference_audio_path, 
                        language=target_language
                    )
                    
                    # Type casting: converte l'array C-style di numpy in un tensore ottimizzato residente su PyTorch.
                    wav_tensor = torch.tensor(wav_array)
                    
                    # Definisce l'indiciatore iterativo di fine-lettura per il layer di buffer di base al clipping appena istanziato.
                    end_sample = current_start_sample + len(wav_tensor)
                    
                    generated_clips.append((current_start_sample, end_sample, wav_tensor))
                    
                    # Tracking dinamico del frame totale più elevato (resize indiretto della timeline container).
                    if end_sample > max_sample_needed:
                        max_sample_needed = end_sample
                        
                    # Shift dell'offset puntatore per interpolare sub-paragrafi contigui (nella medesima battuta).
                    current_start_sample = end_sample
            
            # Guard-clause estrema avverso allocazioni hardware erranti (vettori zero size).
            if not generated_clips:
                raise ValueError("Nessun segmento valido da sintetizzare.")
                
            # Preallocazione hard-memory del master mix buffer ("canvas") con silence padding omogeneo.
            final_audio = torch.zeros(max_sample_needed)
            
            # Mux in-memory vettoriale: posiziona per slicing e sovrappone aritmeticamente tutti i clip sul target sample rate.
            for start_sample, end_sample, wav_tensor in generated_clips:
                final_audio[start_sample:end_sample] += wav_tensor
            
            # Gain staging and Mastering (Peak Normalization limit). Assicura il fall-off anti distorsione / alias 
            # nel denaturare clipping dovuti a somma di segnali su frames paralleli.
            if final_audio.max() > 1.0 or final_audio.min() < -1.0:
                final_audio = final_audio / max(final_audio.max(), abs(final_audio.min()))
                
            # Aggiunta di asse fittizio per rispettare la signature del decoder torchaudio (Channel augmentation).
            final_audio = final_audio.unsqueeze(0)
            
            # Flushing persistente del buffer su disco locale come RIFF PCM (.WAV).
            torchaudio.save(output_path, final_audio, SAMPLE_RATE)
            
            return output_path
            
        except Exception as e:
            # Trap graceful per far rimbalzare eccezioni non gestite direttamente su middleware o UI.
            return f"[ERRORE DI SINTESI VOCALE]: {str(e)}"