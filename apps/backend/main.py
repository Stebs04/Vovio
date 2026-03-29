
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import TEMP_DIR
from utils.video_processing import extract_audio, merge_audio_video
from agents.transcriber import TranscriptionAgent
from agents.translator import TranslationAgent
from agents.synthesizer import SynthesizerAgent

# Store in-memory temporaneo per monitorare lo stato dei job asincroni
job_store = {}

app = FastAPI(
    title="Vovio Backend",
    description="API per la trascrizione, traduzione e doppiaggio automatizzato di video.",
    version="0.1.0"
)

# Configurazione CORS per consentire le comunicazioni dal frontend locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inizializzazione single-instance degli agenti per ottimizzare l'uso delle risorse e ridurre la latenza
transcriber_agent = TranscriptionAgent()
synthesizer_agent = SynthesizerAgent()


class TranslationRequest(BaseModel):
    """
    Payload per la richiesta di traduzione.
    Supporta sia testo semplice (str) che il formato strutturato restituito da Whisper (list).
    """
    text: str | list       
    target_language: str


class DubbingRequest(BaseModel):
    """
    Payload per la richiesta di doppiaggio.
    Contiene i riferimenti al video, il testo tradotto e la lingua di destinazione.
    """
    video_filename: str
    translated_text: str | list
    target_language: str


@app.get("/")
async def get_status():
    """Endpoint di health-check per verificare lo stato e l'uptime del backend."""
    return {
        "status": "operational",
        "app": "vovio",
        "version": "0.1.0"
    }


@app.post("/api/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    """
    Riceve un file video, ne estrae la traccia audio e restituisce la trascrizione testuale.
    """
    video_path = TEMP_DIR / file.filename
    
    # Salvataggio asincrono del file video caricato
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())

    # Estrazione dell'audio necessaria per l'elaborazione del modello ASR (Automatic Speech Recognition)
    audio_path = extract_audio(str(video_path))
    transcription_data = transcriber_agent.transcribe(str(audio_path))

    return {"filename": file.filename, "transcription": transcription_data}


@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    """
    Traduce il testo fornito nella lingua di destinazione specificata.
    Preserva la struttura JSON dei segmenti se l'input proviene da Whisper.
    """
    # Istanziamo l'agente di traduzione con la lingua target impostata
    translator = TranslationAgent(target_language=request.target_language)
    
    # Normalizzazione: serializziamo le strutture complesse per mantenere i metadati temporali nel prompt del LLM
    payload = request.text if isinstance(request.text, str) else json.dumps(request.text)
    translated_text = translator.translate(payload)
    
    return {"original_text": request.text, "translated_text": translated_text}


def process_dubbing_task(job_id: str, request: DubbingRequest):
    """
    Worker in background per l'elaborazione asincrona del doppiaggio:
    1. Parsing e sanitizzazione del testo da sintetizzare
    2. Clonazione vocale e generazione della nuova traccia audio (TTS)
    3. Muxing dell'audio generato con il video originale
    """
    try:
        job_store[job_id]["status"] = "processing"
        
        video_path = TEMP_DIR / request.video_filename
        # Si assume che l'audio di riferimento per il voice cloning sia il .wav estratto in fase di trascrizione
        reference_audio_path = TEMP_DIR / f"{Path(request.video_filename).stem}.wav"
        
        text_to_speak = request.translated_text
        
        # Gestione flessibile del payload testuale: decodifica di stringhe JSON e unione di segmenti multipli
        try:
            parsed_data = json.loads(text_to_speak) if isinstance(text_to_speak, str) else text_to_speak
            if isinstance(parsed_data, list):
                # Estrae e concatena solo le porzioni di testo effettivo ignorando i metadati opzionali
                text_to_speak = " ".join([
                    item.get("text", "") 
                    for item in parsed_data 
                    if isinstance(item, dict) and "text" in item
                ])
        except Exception:
            # Fallback passivo: in caso di errori di parsing si tenta di passare il dato non elaborato al sintetizzatore
            pass

        # Generazione della traccia audio doppiata localizzata
        dubbed_audio_path = synthesizer_agent.generate_audio(
            text=text_to_speak,
            target_language=request.target_language,
            reference_audio_path=str(reference_audio_path)
        )
        
        if dubbed_audio_path.startswith("[ERRORE"):
            raise ValueError(f"Fallimento durante il TTS: {dubbed_audio_path}")

        final_video_filename = f"final_{request.target_language}_{request.video_filename}"
        final_video_path = TEMP_DIR / final_video_filename

        # Integrazione della nuova sorgente audio nel flusso video originario
        merge_audio_video(
            video_path=str(video_path),
            audio_path=dubbed_audio_path,
            output_path=str(final_video_path)
        )
        
        # Commit di successo nello state store
        job_store[job_id].update({
            "status": "completed",
            "result": {"final_video": final_video_filename}
        })
        
    except Exception as e:
        # Gestione centralizzata delle eccezioni per prevenire il fallimento silenzioso del worker
        job_store[job_id].update({
            "status": "failed",
            "error": str(e)
        })

@app.post("/api/dub", status_code=status.HTTP_202_ACCEPTED)
async def generate_dubbing(request: DubbingRequest, background_tasks: BackgroundTasks):
    """
    Accetta una richiesta di doppiaggio inoltrando l'elaborazione intensiva a un background worker.
    Fornisce contestualmente un job_id abilitando i meccanismi di polling lato client.
    """
    job_id = str(uuid4())
    job_store[job_id] = {
        "status": "pending",
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(process_dubbing_task, job_id, request)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Il doppiaggio è in corso. Usa il job_id per monitorare lo stato."
    }


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Endpoint per gestire il download o lo streaming dei file video generati dalla pipeline."""
    file_path = TEMP_DIR / filename

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Endpoint di polling per ispezionare asincronamente lo stadio di avanzamento dei task."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job non trovato!")
    return job_store[job_id]
