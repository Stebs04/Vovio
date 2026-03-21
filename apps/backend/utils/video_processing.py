from pathlib import Path
from moviepy import VideoFileClip, AudioFileClip
import config

def extract_audio(video_path: str) -> Path:
    """
    Estrae la traccia audio da un file video sorgente.
    Usa MoviePy per l'estrazione e salva il risultato come WAV nella directory temporanea.

    Args:
        video_path (str): Percorso del file video da elaborare.

    Returns:
        Path: Oggetto Path puntante al file audio estratto.
    """
    # Recupera il nome base del file (stem) per mantenere consistenza nei nomi
    stem = Path(video_path).stem
    
    # Costruisce il path di output nella cartella temporanea definita in config
    audio_output = config.TEMP_DIR / f"{stem}.wav"
    
    # Context Manager per gestire in sicurezza l'apertura e chiusura del file video.
    # Garantisce il rilascio del file handle anche in caso di eccezioni.
    with VideoFileClip(video_path) as video:
        # Scrive la traccia audio su disco usando le impostazioni di default (spesso .wav non compresso o mp3)
        # Qui l'estensione nel path forza il formato.
        video.audio.write_audiofile(str(audio_output), logger=None)
        
    return audio_output


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Combina un flusso video esistente con una nuova traccia audio (Muxing).
    
    Args:
        video_path (str): Video sorgente originale.
        audio_path (str): Nuova traccia audio da iniettare.
        output_path (str): Percorso finale dove salvare il risultato.

    Returns:
        str: Il path del file di output.
    """
    # Caricamento del video e della nuova traccia audio in memoria
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)
    
    try:
        # Imposta la nuova traccia audio, sostituendo quella originale se presente
        final_video = video_clip.set_audio(audio_clip)
        
        # Scrive il video su disco usando codec standard per compatibilità (H.264 + AAC)
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            logger=None  # Riduce il rumore nei log se non necessario
        )
    finally:
        # Best Practice: Chiudere esplicitamente le clip per rilasciare i lock sui file
        video_clip.close()
        audio_clip.close()
        
    return output_path

    
