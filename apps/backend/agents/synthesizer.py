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


    # Metodo per generare audio (nota: riceve `self` nella firma suggerendo che sia in origine parte di una classe).
    def generate_audio(self, segments: list[dict], target_language: str, reference_audio_path: str, progress_callback=None):
        # Entra nel blocco try-except principale per gestire l'intero workflow di generazione tutelandosi dagli errori runtime.
        try:
            # Crea il nome del file di output basandosi sulla lingua target impostata (es. 'dubbed_it.wav').
            output_filename = f"dubbed_{target_language}.wav"
            # Converte l'oggetto Path combinato col nome in una stringa di path assoluto per il salvataggio nella directory temporanea.
            output_path = str(TEMP_DIR / output_filename)
            
            # Una lista per accumulare tutti i singoli tensori audio derivati dalla sintesi graduale.
            audio_tensors = []
            # Definizione della frequenza di campionamento (Sample Rate) specifica e fissa dell'architettura del modello XTTS_v2.
            SAMPLE_RATE = 24000 
            # Inizializza il contatore del tempo (in secondi) relativo a tutto l'audio sintetizzato finora, per gestire il timing dei segmenti.
            current_time = 0.0  
            
            # Ciclo iterativo tramite tutti i segmenti vocali forniti in input; ciascuno possiede il suo testo e dei trigger temporali.
            for i, segment in enumerate(segments):
                # Se è stata fornita una funzione di callback (utile spesso per le progress bar in UI)...
                if progress_callback:
                    # ...calcola la percentuale del progresso in base all'iterazione.
                    current_pct = int((i / len(segments)) * 100)
                    # Invoca la callback passando la nuova % e una flag "synthesizing".
                    progress_callback(current_pct, "synthesizing")
                
                # Estrae il chunk testuale dal segmento proteggendosi da chiavi inesistenti grazie al fallback `get` ('').
                text_chunk = segment.get('text', '')
                # Estrae il timecode iniziale in secondi in cui l'audio dovrebbe innestarsi rispetto all'inizio del file media generale.
                start_time = segment.get('start', 0.0)
                
                # Se la stringa testuale dovesse farsi trovare vuota (o di soli spazi), bypassa la sintesi saltando alla successiva.
                if not text_chunk.strip(): 
                    continue
                
                # Se la durata d'audio generata finora è in ritardo rispetto al momento in cui dovrebbe partire questo nuovo segmento audio...
                if current_time < start_time:
                    # ...determina in secondi quanto 'silenzio' bisogna inserire per sincronizzare la timeline audio locale rispetto allo start.
                    duration_seconds = (start_time - current_time)
                    
                    # Moltiplicando la durata per il sample rate otteniamo l'esatto ammontare in sample rate di cui abbiamo bisogno.
                    samples = int(duration_seconds * SAMPLE_RATE)
                
                    # Viene instanziato un vuoto tensore tramite `zeros` in PyTorch corrispondente proprio a un rumore pari allo step zero (silenzio).
                    samples_number = torch.zeros(samples)
                
                    # Si concatena poi il ritardo alla lista dei futuri tensori.
                    audio_tensors.append(samples_number)
            
                    # Si allinea il timer cronologico per fare matching con il tempo di partenza dello speech attuale.
                    current_time = start_time
                # -----------------------------------------------
                
                # Chiamata centrale all'engine del modello XTTS_v2 che gestisce la pronuncia. Parametri: test chunk pulito, clone-audio ref, idioma targe.
                wav_array = self.tts.tts(
                    text=text_chunk, 
                    speaker_wav=reference_audio_path, 
                    language=target_language
                )
                
                # Il ritorno array va avvolto in un tipo compatibile Tensore per renderlo pronto per le operazioni successive colme di librerie dedicate PyTorch.
                wav_tensor = torch.tensor(wav_array)
                # Si accoda la traccia prodotta e codificata via Tensore al pool.
                audio_tensors.append(wav_tensor)
                
                # Si aggiorna il cronometro virtuale interno aumentando lo stesso del tempo in secondi per cui canta il motore: `numero vettori` fratto `SR`.
                current_time += len(wav_tensor) / SAMPLE_RATE
            
            # Dopo terminato il looping, se per puro asincrono le stringhe fossero andate perse nel flusso lasciando tensori assenti, cattură.
            if not audio_tensors:
                # Emette una voluta eccezione (poi rigettata al catcher locale) intercettando stati inattesi a valle per impedire output corrotti.
                raise ValueError("Nessun segmento valido da sintetizzare.")
                
            # Il vero rendering che incolla i vettori di speech unendoli nel medesimo layer tensoriale tramite uncat lungo la matrice principale zero-dimension.
            final_audio = torch.cat(audio_tensors).unsqueeze(0)
            # Salva attraverso modulo dedicato torchaudio. Inseriamo la forma file `.wav` nel target designato avvalendoci della Rate prefissata originale del modello testuale.
            torchaudio.save(output_path, final_audio, SAMPLE_RATE)
            
            # Una volta concesso file path concesso su file system in I/O positivo al termine elaborazione viene renderne in exit il medesimo Path locale in String.
            return output_path
            
        # Catchem all per raccogliere qualsiasi imprevisto esitante l'ambiente in locale, utile per evitare crash interi della pipeline e segnalarle agilmenete sull'upper layer API.
        except Exception as e:
            return f"[ERRORE DI SINTESI VOCALE]: {str(e)}"