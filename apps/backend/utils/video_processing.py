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
    Combina un flusso video esistente con una nuova traccia audio (operazione di Muxing).
    Sovrascrive l'audio originale con quello fornito, garantendo la compatibilità
    temporale e gestendo in sicurezza la deallocazione delle risorse in memoria.
    """
    # Inizializza i decoder di MoviePy per avvolgere i flussi multimediali
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)
    
    try:
        # Hard-clipping di sicurezza: se l'audio sintetizzato supera la durata del 
        # video originale, taglia l'eccedenza. Questo evita l'allungamento della 
        # timeline finale con conseguenti frame video "congelati" (neri o statici).
        if audio_clip.duration > video_clip.duration:
            audio_clip = audio_clip.subclip(0, video_clip.duration)
            
        # Inietta la nuova traccia audio nel container video (sostituendo la precedente)
        final_video = video_clip.with_audio(audio_clip)
        
        # Esegue il rendering finale su disco.
        # Utilizza H.264 per il video e AAC per l'audio per garantire massima compatibilità (Web/Mobile).
        # Il logger è disabilitato per ridurre il blocco di I/O sulla console durante il processo.
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            logger=None  
        )
    finally:
        # Cleanup critico: forza il rilascio dei file handle e dei subprocessi FFmpeg allocati.
        # Il blocco finally garantisce che non ci siano memory leak anche in caso di eccezioni d'encoding.
        video_clip.close()
        audio_clip.close()
        
    return output_path