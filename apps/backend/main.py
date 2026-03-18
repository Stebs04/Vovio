
# Importa la classe FastAPI e le utilità per la gestione dei file dal modulo fastapi
from fastapi import FastAPI, UploadFile, File
# Importa la directory temporanea dal file di configurazione
from config import TEMP_DIR
# Importa la funzione per estrarre l'audio dal modulo di elaborazione video
from utils.video_processing import extract_audio
# Importa la classe TranscriptionAgent dal modulo degli agenti di trascrizione
from agents.transcriber import TranscriptionAgent

# Inizializza l'applicazione FastAPI
app = FastAPI()
# Crea un'istanza dell'agente di trascrizione
transcriber_agent = TranscriptionAgent()

# Definisce un endpoint GET alla radice '/' per verificare lo stato dell'applicazione
@app.get('/')
# Definisce la funzione asincrona per gestire la richiesta di stato
async def get_status():
    # Restituisce un dizionario JSON con le informazioni di stato
    return {
        # Indica che il servizio è operativo
        "status": "operational",
        # Specifica il nome dell'applicazione
        "app": "vovio",
        # Indica la versione attuale dell'applicazione
        "version": "0.1.0"
    }

# Definisce un endpoint POST su '/api/transcribe' per gestire il caricamento e la trascrizione dei video
@app.post("/api/transcribe")
# Definisce la funzione asincrona che accetta un file caricato come input obbligatorio
async def process_video(file: UploadFile = File(...)):
    # Costruisce il percorso completo per salvare il file video nella directory temporanea utilizzando il nome originale del file
    video_path = TEMP_DIR / file.filename
    # Apre il file di destinazione nel percorso specificato in modalità scrittura binaria ('wb')
    with open(video_path, "wb") as buffer:
        # Legge in modo asincrono il contenuto del file caricato e lo scrive nel file aperto su disco
        buffer.write(await file.read())
    # Estrae la traccia audio dal file video salvato e ottiene il percorso del file audio generato
    audio_path = extract_audio(str(video_path))
    # Esegue la trascrizione del file audio utilizzando il metodo dell'agente di trascrizione
    transcription_data = transcriber_agent.transcribe(str(audio_path))
    # Restituisce una risposta JSON contenente il nome del file originale e i dati della trascrizione risultante
    return {"filename": file.filename, "transcription": transcription_data}
