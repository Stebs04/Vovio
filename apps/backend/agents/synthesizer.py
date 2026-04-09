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
        
       # Gestione dell'accelerazione hardware
        cuda_val = os.environ.get("USE_CUDA", "0").lower()
        use_cuda_env = cuda_val in ["1", "true", "t", "yes"]
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
    
    def generate_audio(self, segments: list[dict], target_language: str, reference_audio_path: str, target_duration_sec: float = None, progress_callback=None):
        """
        Sintetizza i frammenti vocali e li posiziona su una timeline audio esatta.
        Garantisce che la traccia finale duri esattamente quanto richiesto, ideale per un muxing perfetto.
        """
        # Inizio di un blocco try-except per isolare e intercettare qualsiasi errore durante il ciclo di sintesi.
        try:
            # Genera il nome del file di output dinamicamente concatenando il codice lingua (es. dubbed_it.wav).
            output_filename = f"dubbed_{target_language}.wav"
            # Costruisce il percorso assoluto sul disco, innestandolo nella specifica directory temporanea.
            output_path = str(TEMP_DIR / output_filename)
            
            # Imposta la frequenza di campionamento fissa a 24kHz compatibile coi tensori prodotti dal modello XTTS.
            SAMPLE_RATE = 24000 
            # Inizializza un vettore vuoto che funzionerà da buffer in-memory per immagazzinare le singole clip generate.
            generated_clips = []
            # Mantiene in memoria il posizionamento temporale finale dell'ultimo clip elaborato per evitare overlap.
            last_end_sample = 0 
            
            # 1. DEFINIAMO LA LUNGHEZZA ESATTA DEL CANVAS AUDIO (LA "TELA")
            # Controller per assicurarsi che un parametro base di limitazione temporale sia stato esplicitamente servito in ingresso.
            if target_duration_sec is None:
                try:
                    # Interroga i layer sottostanti al file di referenza per estrarre la root struct dei metadati originali.
                    ref_info = torchaudio.info(reference_audio_path)
                    # Calcola i secondi effettivi convertendo il conteggio dei frames con diviso il sample rate primario.
                    target_duration_sec = ref_info.num_frames / ref_info.sample_rate
                except Exception:
                    # Condizione di scarto ed handling fail-safe contro stream corrotti; la traccia è generata come buffer zero length.
                    target_duration_sec = 0.0

            # Scala la durata da valore reale in Float ai campioni necessari rappresentabili in matrice Array allocando le frequenze.
            master_total_samples = int(target_duration_sec * SAMPLE_RATE)
            
            # Inizia un ciclo d'orchestrazione sui segmenti semantici pre formattati iniettati a monte dal modulo di trascrizione locale.
            for i, segment in enumerate(segments):
                # Validazione della funzione esterna inieittata per notificare in asincrono al modulo upstream lo scaling d'avanzamento.
                if progress_callback:
                    # Calcola il rate di completamento con scalare a cento.
                    current_pct = int((i / len(segments)) * 100)
                    # Trigger che dispatccia lo scope UI o Job Manager allo status sintetizzazione locale progressivo.
                    progress_callback(current_pct, "synthesizing")
                
                # Cerca l'estratto esatto di token str dalla collection e fa fallback stringa vuota al trigger per index miss match pass.
                text_chunk = segment.get('text', '')
                # Estrae il timestamp float in secondi dalla pipeline di VAD originaria.
                start_time = segment.get('start', 0.0)
                
                # Layer di filtering: Elimina battute mute o puramente white space che farebbero bloccare staticamente il TTS generator.
                if not text_chunk.strip(): 
                    # Scarta questo indice e processa l'operatore prossimo al dispatch logico buffer.
                    continue
                
                # Splitta in porzioni sub ottimali il costrutto estraibile tramite function adibita per ridurre fall-rate ed overlap d'allucinazioni su XTTS.
                sub_chunks = self._chunk_text(text_chunk, max_chars=200)
                # Calcola il campione d'offset d'inizio target dalla baseline float applicando la scala di frequenza nominale locale.
                current_start_sample = int(start_time * SAMPLE_RATE)
                
                # Check d'integrità dinamico contro la colissione sonora "overlap". Analizza il delta con la precendete esecuzione vettoriale.
                if current_start_sample < last_end_sample:
                    # Corregge matematicamente facendo back-shift allineandolo a confine della struttura precedente per preservare chiarezza vocalica totale.
                    current_start_sample = last_end_sample
                
                # Avanza all'interno delle frammentazioni semantiche derivate (micro frasi per alleggerire attention network).
                for sub_text in sub_chunks:
                    # Utilizza l'handler deep learning in zero-shot inference tramite core di referenza speaker clonata con coqui library framework.
                    wav_array = self.tts.tts(
                        text=sub_text, 
                        speaker_wav=reference_audio_path, 
                        language=target_language
                    )
                    
                    # Converte la list-like struttura python memory managed passata da back API a Tensor PyTorch compilato in C-struct.
                    wav_tensor = torch.tensor(wav_array)
                    # Deriva metricamente la length vettoriale (frame fine) sommando il sample index d'inizio al computo del tensore scalare generato locale.
                    end_sample = current_start_sample + len(wav_tensor)
                    
                    # Store tracking: Aggancia l'inizio offset matematico locale, punto terminale vettoriale predetto locale e buffer audio originato in buffer array.
                    generated_clips.append((current_start_sample, end_sample, wav_tensor))
                    # Shifta dinamicamente il marker per preallinearsi alla terminazione dell'array attuale.
                    current_start_sample = end_sample
                
                # Aggiorna tracciamento global interation posizionando il gate d'astrazione come salvataggio boundary limit per validazione offset cross frase locale.
                last_end_sample = current_start_sample
            
            # Scarto d'esecuzione. Segnala operazione vacante e lancia trigger standard verso macro API su list loop fallace locale vuoto strutturato d'error management.
            if not generated_clips:
                # Resettare a pipeline vuota lo stato locale pass.
                raise ValueError("Nessun segmento valido da sintetizzare.")
                
            # 2. CREIAMO LA TRACCIA VUOTA DELLA LUNGHEZZA PERFETTA
            # Valutiamo la grandezza massima generata o imposta per prevenire memory exception allocate.
            final_length = max(last_end_sample, master_total_samples)
            # Inizializziamo il tensore PCM vuoto pre-creando sample rates binari zero (mute canvas background vector stream builder allocation) della master length locale reale.
            final_audio = torch.zeros(final_length)
            
            # Ripetiamo il buffer vettoriale originario e mappiamo d'append sull'estrazione master tramite lacing ed additive mixing overlay puro.
            for start_sample, end_sample, wav_tensor in generated_clips:
                # Layering sonoro. Aggiunge dinamicamente per reference di range index il tensor nel canvas pre istanziato locale.
                final_audio[start_sample:end_sample] += wav_tensor
            
            # 3. TAGLIO DI PRECISIONE AL MILLISECONDO
            # Effettuiamo un fall-off esplicito sul marker di master timing allocato originale pre process di sintesi.
            if master_total_samples > 0:
                # Applichiamo slice destrutturato matematico del vettore binario tagliando le sbavature posteriori generate temporalmente in eccedente limitate.
                final_audio = final_audio[:master_total_samples]
            
            # Routine di Gain Normalization Peak-limit. Corregge le sbordature (clip in rosso) oltre il range floating standard (-1.0;1.0 bit struct) a salvaguardia di pop stream render audio e compression dynamic struct pre disk.
            if final_audio.max() > 1.0 or final_audio.min() < -1.0:
                # Mantiene la gain proportion originaria limitando l'RMS a livello normalizzato 0dbFs (1 Float range limit peak) tramite rapporto master gain peak allocation div locale divisione massima range limit float scalare div iso.
                final_audio = final_audio / max(final_audio.max(), abs(final_audio.min()))
                
            # Adatta la single array track unificata creata con pseudo-mono channel aggiungendo asse frontale. Requisito torchaudio (n channel padding front offset unsqueeze method).
            final_audio = final_audio.unsqueeze(0)
            # Scrive e flusha buffer tensor torchaudio salvando come disco payload master WAV con rate encoding.
            torchaudio.save(output_path, final_audio, SAMPLE_RATE)
            
            # Rilascia puntatore e cede handling file locale in string come exit signal handler di conformità pass API.
            return output_path
            
        # Exception handler per fault catch in isolamento pass stream back-trace d'ispezione al chiamante locale.
        except Exception as e:
            # Trap exception general purposing standard per l'aggancio da master thread dispatcher loop return trace pre formattato per front API local scope caller string reference response fallback d'invio asincrono locale UI string display callback UI message fall.
            return f"[ERRORE DI SINTESI VOCALE]: {str(e)}"