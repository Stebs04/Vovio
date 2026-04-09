# Importa la classe Path dal modulo standard pathlib per una gestione robusta e multipiattaforma dei percorsi del file system.
from pathlib import Path
# Importa le interfacce principali di MoviePy (standard 2.x compatibile) per la decodifica, la manipolazione e l'orchestrazione degli stream A/V.
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
# Importa il modulo di configurazione globale del backend, necessario per risolvere i path della directory temporanea.
import config

def extract_audio(video_path: str) -> Path:
    """
    Estrae e demuxa la traccia audio nativa da un file video sorgente limitando l'overhead di transcodifica.
    Salva il raw stream sonoro esportato in formato PCM lineare (WAV) all'interno della directory temporanea.
    """
    # Estrae la radice del nome del file (es: "video" da "video.mp4") per generare i nomi dei file temporanei.
    stem = Path(video_path).stem
    # Compone, mediante la classe Path, il tracciato completo di destinazione nella cartella di appoggio.
    audio_output = config.TEMP_DIR / f"{stem}.wav"
    
    # Apre lo stream video avvalendosi di un Context Manager per assicurare il corretto rilascio delle risorse (file non bloccati a fine esecuzione).
    with VideoFileClip(video_path) as video:
        # Gestione dei casi limite per file privi di container audio.
        if video.audio is None:
            # Importa AudioClip localmente (Lazy Import) per non appesantire l'esecuzione laddove non strettamente necessario.
            from moviepy import AudioClip
            # Inizializza una traccia silenziosa fittizia, vitale al processo e alle integrazioni successive qualora la sorgente ne fosse priva.
            empty_audio = AudioClip(lambda t: [0,0], duration=1)
            # Finalizza operativamente su disco la traccia inerte impostando una frequenza sample standard.
            empty_audio.write_audiofile(str(audio_output), fps=44100, logger=None)
        else:
            # Completa l'operazione estraendo e scrivendo su disco il canale audio originale con i logger silenziati.
            video.audio.write_audiofile(str(audio_output), logger=None)
        
    # Restituisce l'oggetto Path che fungerà da indicatore alla posizione del file per i passaggi di elaborazione successivi della pipeline.
    return audio_output


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Esegue il mixaggio fra il video originale e l'audio tradotto generato testualmente (TTS).
    Implementa le logiche di Ducking (attenuazione volume) sulla base originale per preservare suoni naturali senza sormontare il doppiaggio.
    """
    # Crea l'istanza principale in lettura associando il buffer in memoria della traccia sorgente visuale.
    video_clip = VideoFileClip(video_path)
    # Istanzia il lettore designato alla gestione della nuova voce sintetica doppiata.
    new_voice_clip = AudioFileClip(audio_path)
    # Variabile designata per raccogliere il mix temporale, pre-allocata per garantirne corretta pulizia nel costrutto finally.
    mixed_final_audio = None
    
    # Delimita l'inizializzazione e successiva finalizzazione per arginare qualsiasi blocco in termini I/O dovuti agli script FFmpeg in caso di guasto.
    try:
        # Prevenzione di overflow temporale: evita che la traccia doppiata si prolunghi oltre la naturale estensione del file video originale.
        if new_voice_clip.duration > video_clip.duration:
            # Taglio netto per preservare stabilità della tempistica con le API MoviePy 2.x standardizzate.
            try:
                # Interfaccia standard v2: restringe puntualmente la clip.
                new_voice_clip = new_voice_clip.subclipped(0, video_clip.duration)
            except AttributeError:
                # Interfaccia retrocompatibile: ripiego sicuro per installazioni su precedenti iterazioni della libreria genitrice (MoviePy v1).
                new_voice_clip = new_voice_clip.subclip(0, video_clip.duration)
            
        # Isola internamente l'appoggio sonoro proveniente dal lettore visuale istanziato all'avvio.
        original_audio = video_clip.audio
        
        # Validatore essenziale: bypassa l'eventualità di operare riduzioni del volume su tranci non effettivamente caricati se mancanti.
        if original_audio is not None:
            # Abbassamento progressivo e ridimensionamento della base sorgente tramite Ducking.
            try:
                # Forza il declassamento prestazionale del frame scalando il volume standard al 10%.
                background_audio = original_audio.with_volume_scaled(0.10)
            except AttributeError:
                # Attiva nuovamente dinamiche pre-storicizzate compatibili in sostituzione operativa della regola precedente decaduta.
                background_audio = original_audio.volumex(0.10)
                
            # Operatività del mix parallelo: istruzione per far risuonare congiuntamente la base musicale smorzata congiuntamente al parlato netto.
            mixed_final_audio = CompositeAudioClip([background_audio, new_voice_clip])
            # Innesta la traccia fusa all'interno delle direttive visuali preimpostate della macro architettura stream originaria.
            final_video = video_clip.with_audio(mixed_final_audio)
        else:
            # Configurazione base e fluida laddove il file generico non ha preconfigurati sonori e dunque accetta a sé il doppiaggio esclusivo.
            final_video = video_clip.with_audio(new_voice_clip)
        
        # Scatena l'inizio formale della codifica in salvataggio definitivo indirizzando output sul disco interno e istanziando pool thread multiasincroni per alleggerire.
        final_video.write_videofile(
            output_path, 
            # Codec visuale garantisce efficienza, ridotte cadute prestazionali online/applicative in appositi formati di file standard MP4.
            codec="libx264", 
            # Inserisce l'AAC standard che non satura storage rendendosi accessibile ad internet e player mobile.
            audio_codec="aac",
            # Sacrifica qualità d'impacchettamento prediligendo latenze in millisecondi in output operando un bypass rapido.
            preset="ultrafast",
            # Ottimizza hardware impiegando thread attivi di elaborazione multicanale simultanei, idealmente sfruttando cores multi-core.
            threads=4,
            # Monitoraggio e controllo tramite console esterna visiva dei percorsi di finalizzazione del frammento intero di dati riallocati in FFMpeg.
            logger="bar"
        )
    # Ciclo rigido e asseverativo della fine formale d'incapsulazione: libera risorse allocate internamente di Python Garbage Collector bloccate sul file system limit host locale.
    finally:
        # Cessa forzatamente lo streaming dei flussi d'immagini pre-sorgente in uso in modo da rimuovere ogni ingombro in RAM server.
        video_clip.close()
        # Assolve e interrompe forzatamente in modo distruttivo buffer collegati alla linea audio generata allocamente sui tasker in coda.
        new_voice_clip.close()
        # Svincola in salvaguardia eventuali trame del miscelatore allocate dinamicamente se pre-esiste interruzione o fail logico limit.
        if mixed_final_audio is not None:
            try:
                mixed_final_audio.close()
            # Ignoriamo le eccezioni per un chiusura non bloccante.
            except Exception:
                pass
        
    # Termina indicando alla logica genitrice (Route handler FastAPI) dove recuperare sul File System del server ospite il prodotto della pipeline testè chiusa validamente al completamento.
    return output_path