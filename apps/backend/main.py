
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

# Store in-memory per tracciare lo stato dei job asincroni
job_store = {}

app = FastAPI(
    title="Vovio Backend",
    description="API per trascrizione, traduzione e doppiaggio automatizzato di video.",
    version="0.1.0"
)

# Configura i CORS per permettere le chiamate dal frontend locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inizializza gli agenti all'avvio per minimizzare la latenza delle richieste successive
transcriber_agent = TranscriptionAgent()
synthesizer_agent = SynthesizerAgent()


class TranslationRequest(BaseModel):
    """
    Payload per le richieste di traduzione.
    Supporta stringhe semplici o strutture dati restituite da Whisper.
    """
    text: str | list       
    target_language: str


class DubbingRequest(BaseModel):
    """
    Payload per le richieste di doppiaggio.
    Contiene il riferimento al video originale, il testo tradotto e la lingua target.
    """
    video_filename: str
    translated_text: str | list
    target_language: str


@app.get("/")
async def get_status():
    """Endpoint di health-check dell'API."""
    return {
        "status": "operational",
        "app": "vovio",
        "version": "0.1.0"
    }


@app.post("/api/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    """
    Riceve un video, ne estrae l'audio ed esegue la trascrizione tramite l'agente ASR.
    """
    video_path = TEMP_DIR / file.filename
    
    # Salva il file caricato su disco
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())

    # Estrae l'audio e avvia la trascrizione
    audio_path = extract_audio(str(video_path))
    transcription_data = transcriber_agent.transcribe(str(audio_path))

    return {"filename": file.filename, "transcription": transcription_data}


@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    """
    Endpoint per tradurre il testo estratto dalla trascrizione.
    Gestisce sia stringhe singole che liste di frammenti (chunks) provenienti da Whisper.
    """
    # Inizializza l'agente di traduzione con la lingua di destinazione richiesta
    translator = TranslationAgent(target_language=request.target_language)
    
    # Se il payload di input è una lista (tipico array di segmenti da Whisper)
    if isinstance(request.text, list):
        translated_chunks = []
        for chunk in request.text:
            # Verifica che il chunk sia un dizionario valido contenente la chiave "text"
            if isinstance(chunk, dict) and "text" in chunk:
                # Esegue la traduzione per il singolo frammento
                adapted_text = translator.translate(chunk["text"])
                
                # Crea una copia del chunk originale per preservare i timestamp
                translated_chunk = chunk.copy()
                translated_chunk["text"] = adapted_text
                
                # Aggiunge il chunk tradotto alla lista finale
                translated_chunks.append(translated_chunk)
                
        return {"original_text": request.text, "translated_text": translated_chunks}
    
    else:
        # Fallback per payload composti da una singola stringa grezza
        translated_text = translator.translate(request.text, duration_second=0.0)
        return {"original_text": request.text, "translated_text": translated_text}

def process_dubbing_task(job_id: str, request: DubbingRequest):
    """
    Worker in background per gestire l'intero flusso di doppiaggio:
    1. Parsing del testo da sintetizzare.
    2. Generazione dell'audio (TTS) clonando la voce originale.
    3. Unione del nuovo audio con il video originale.
    """
    try:
        job_store[job_id] = {"status": "processing", "progress": 0, "stage": "initializing"}
        
        def update_progress(progress_val: int, stage_label: str):
            if job_id in job_store:
                job_store[job_id].update({"progress": progress_val, "stage": stage_label})

        video_path = TEMP_DIR / request.video_filename
        # Si assume che l'audio di riferimento sia stato già estratto in fase di trascrizione
        reference_audio_path = TEMP_DIR / f"{Path(request.video_filename).stem}.wav"
        
        text_to_speak = request.translated_text
        
        # Gestisce il payload decodificando stringhe JSON e concatenando i segmenti
        try:
            parsed_data = json.loads(text_to_speak) if isinstance(text_to_speak, str) else text_to_speak
            if isinstance(parsed_data, list):
                # Estrae e unisce solo il testo effettivo ignorando i metadati
                text_to_speak = " ".join([
                    item.get("text", "") 
                    for item in parsed_data 
                    if isinstance(item, dict) and "text" in item
                ])
        except Exception:
            # Fallback per passare il dato grezzo in caso di errori formattazione
            pass

        # Genera il nuovo stream audio
        dubbed_audio_path = synthesizer_agent.generate_audio(
            text=text_to_speak,
            target_language=request.target_language,
            reference_audio_path=str(reference_audio_path),
            progress_callback=update_progress
        )

        update_progress(90, "merging_video")
        
        if dubbed_audio_path.startswith("[ERRORE"):
            raise ValueError(f"Fallimento TTS: {dubbed_audio_path}")

        final_video_filename = f"final_{request.target_language}_{request.video_filename}"
        final_video_path = TEMP_DIR / final_video_filename

        # Unisce il nuovo audio con il flusso video originale
        merge_audio_video(
            video_path=str(video_path),
            audio_path=dubbed_audio_path,
            output_path=str(final_video_path)
        )
        
        # Imposta lo stato su completato
        job_store[job_id].update({
            "status": "completed",
            "result": {"final_video": final_video_filename}
        })
        
    except Exception as e:
        # Gestione errori del worker
        job_store[job_id].update({
            "status": "failed",
            "error": str(e)
        })

@app.post("/api/dub", status_code=status.HTTP_202_ACCEPTED)
async def generate_dubbing(request: DubbingRequest, background_tasks: BackgroundTasks):
    """
    Accoda una richiesta asincrona per il doppiaggio di un video.
    Restituisce un job_id per il polling dello stato.
    """
    job_id = str(uuid4())
    job_store[job_id] = {
        "status": "pending",
        "progress": 0,
        "stage": "queued",
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
    """Ritorna in streaming i file generati dalla pipeline."""
    file_path = TEMP_DIR / filename

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Endpoint per il polling dello stato di un job asincrono."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job non trovato")
    return job_store[job_id]

