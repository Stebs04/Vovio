
# --- Imports Standard e Third-Party ---
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

# --- Imports Configurazione e Utility ---
from config import TEMP_DIR
from utils.video_processing import extract_audio

# --- Imports Agenti AI ---
from agents.transcriber import TranscriptionAgent
from agents.translator import TranslationAgent

# --- Inizializzazione App e Servizi ---
app = FastAPI(
    title="Vovio Backend",
    description="API per trascrizione e traduzione video automatizzata",
    version="0.1.0"
)

# Istanza globale dell'agente di trascrizione (modello caricato all'avvio)
transcriber_agent = TranscriptionAgent()

class TranslationRequest(BaseModel):
    """
    Modello Pydantic per la richiesta di traduzione.
    Definisce la struttura attesa per il corpo della richiesta JSON.
    """
    text: str              # Il testo originale da tradurre
    target_language: str   # Il codice della lingua di destinazione (es. "ita", "esp")


# --- Endpoints ---

@app.get('/')
async def get_status():
    """
    Health Check Endpoint.
    
    Restituisce lo stato corrente del servizio, utile per monitoring e heartbeat.
    """
    return {
        "status": "operational",
        "app": "vovio",
        "version": "0.1.0"
    }

@app.post("/api/transcribe")
async def process_video(file: UploadFile = File(...)):
    """
    Pipeline di Trascrizione Video.
    
    1. Upload del file video.
    2. Estrazione della traccia audio.
    3. Trascrizione tramite agente AI.
    
    Returns:
        JSON contenente il nome del file e il risultato della trascrizione.
    """
    # 1. Gestione Upload: Salvataggio del file temporaneo
    video_path = TEMP_DIR / file.filename
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # 2. Pre-processing: Estrazione audio dal video
    # Utilizza ffmpeg (via utils) per separare la traccia audio
    audio_path = extract_audio(str(video_path))
    
    # 3. Core Logic: Esecuzione dell'agente di trascrizione
    transcription_data = transcriber_agent.transcribe(str(audio_path))
    
    return {"filename": file.filename, "transcription": transcription_data}

@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    """
    Endpoint per la traduzione del testo.
    
    Riceve un testo e una lingua di destinazione, istanzia un agente di traduzione
    e restituisce il testo tradotto.
    """
    # Inizializza l'agente di traduzione con la lingua target specificata nella richiesta
    translator = TranslationAgent(target_language=request.target_language)
    
    # Esegue la traduzione del testo
    translated_text = translator.translate(request.text)
    
    # Restituisce il risultato in formato JSON
    return {"original_text": request.text, "translated_text": translated_text}
