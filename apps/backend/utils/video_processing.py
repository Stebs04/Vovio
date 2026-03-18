#Importazione del modulo di editing video per la gestione dei flussi multimediali
from moviepy import VideoFileClip

from pathlib import Path

#Importazione del modulo di configurazione dei path di processamento
import config

def extract_audio(video_path: str):
    #Generazione dello stem
    stem = Path(video_path).stem
    #Definizione del percorso di destinazione
    audio_output = config.TEMP_DIR / f"{stem}.wav"
    #Utilizzo di un Context Manager per garantire il rilascio automatico delle risorse di sistema, indipendentemente dall'esito del processo.
    with VideoFileClip(video_path) as video:
        # Isolamento del flusso audio e persistenza su disco nel formato di output specificato.
        video.audio.write_audiofile(str(audio_output))
    #Restituisco il percorso generato dalla pipeline di trascrizione
    return audio_output



    
