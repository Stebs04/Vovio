#Importazione del modulo di editing video per la gestione dei flussi multimediali
from moviepy import VideoFileClip

def extract_audio(video_path: str, output_audio_path: str):
    #Utilizzo di un Context Manager per garantire il rilascio automatico delle risorse di sistema, indipendentemente dall'esito del processo.
    with VideoFileClip(video_path) as video:
        # Isolamento del flusso audio e persistenza su disco nel formato di output specificato.
        video.audio.write_audiofile(output_audio_path)



    
