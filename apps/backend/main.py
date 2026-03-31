
"""
Modulo principale dell'applicazione Vovio Backend.
Fornisce le API REST per la trascrizione, traduzione e doppiaggio automatizzato di file video.
Gestisce l'orchestrazione dei job asincroni e il ciclo di vita dei modelli AI residenti in memoria.
"""

import json
from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import TEMP_DIR
from utils.video_processing import extract_audio, merge_audio_video
from agents.transcriber import TranscriptionAgent
from agents.translator import TranslationAgent
from agents.synthesizer import SynthesizerAgent

# In-memory data store per il tracciamento dello stato dei job asincroni (es. operazioni di doppiaggio).
# In un ambiente di produzione, si consiglia l'uso di un broker come Redis o un DB persistente.
job_store = {}

# Registry globale per istanziare e mantenere in memoria i modelli AI (singleton pattern implicito).
# Evita l'overhead di caricamento ad ogni singola richiesta HTTP.
agents = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestisce il ciclo di vita (startup e shutdown) dell'applicazione FastAPI.
    Pre-carica i modelli AI pesanti prima di iniziare ad accettare il traffico di rete,
    garantendo che l'API sia reattiva fin dalla prima richiesta (warm-start).
    """
    print("⏳ Avvio istanziazione dei modelli AI in corso (operazione memory-intensive, attendere)...")
    
    # Inizializzazione e allocazione degli agenti AI nel registry globale
    agents["transcriber"] = TranscriptionAgent()
    agents["synthesizer"] = SynthesizerAgent()
    
    print("✅ Modelli AI caricati e allocati correttamente. Server pronto per servire le richieste.")
    
    yield  # Cede il controllo al framework FastAPI per avviare il loop di accettazione HTTP
    
    # Routine di pulizia (teardown) eseguita allo spegnimento del server (es. ricezione SIGTERM/SIGINT)
    print("🛑 Sequenza di spegnimento avviata. Rilascio delle risorse AI dalla memoria allocata...")
    agents.clear()


# Istanziazione dell'applicazione web con configurazione dei metadati
app = FastAPI(
    title="Vovio Backend",
    description="API orchestrator per la pipeline di trascrizione, traduzione testuale e sintesi vocale video.",
    version="0.1.0",
    lifespan=lifespan  # Hook del ciclo di vita registrato sull'istanza
)

# Configurazione del middleware CORS (Cross-Origin Resource Sharing)
# Permette alle Single Page Application locali (es. frontend React/Next.js) di interrogare l'API vovio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranslationRequest(BaseModel):
    """
    Data Transfer Object (DTO) per la validazione delle richieste di traduzione.
    
    Attributes:
        text (str | list): Contenuto sorgente da tradurre (può essere testo raw o dataset strutturato Whisper).
        target_language (str): Identificativo o ISO code della lingua di destinazione.
    """
    text: str | list       
    target_language: str


class DubbingRequest(BaseModel):
    """
    Data Transfer Object (DTO) per la validazione delle richieste di sintesi/doppiaggio.
    
    Attributes:
        video_filename (str): Nome del file video sorgente, reperibile nella folder temporanea isolata.
        translated_text (str | list): Testo tradotto da utilizzare per la sintesi vocale (TTS).
        target_language (str): Identificativo della lingua per modulare l'engine di sintesi.
    """
    video_filename: str
    translated_text: str | list
    target_language: str


@app.get("/")
async def get_status():
    """
    Endpoint di health-check.
    Utilizzato dai load balancer e monitor di sistema per verificare la reachability dell'API.
    """
    return {
        "status": "operational",
        "app": "vovio",
        "version": "0.1.0"
    }


@app.post("/api/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    """
    Endpoint per il caricamento, l'estrazione audio e la trascrizione di un contenuto video.
    
    Args:
        file (UploadFile): Stream binario multipart del file video codificato in ingresso.
        
    Returns:
        dict: Payload contenente il nome del file e i dati relazionali della trascrizione (ASR).
    """
    # Mappa il file caricato nel path temporaneo di elaborazione del filesystem
    video_path = TEMP_DIR / file.filename
    
    # Persiste in streaming il file video sul disco per evitare l'esaurimento della memoria RAM
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())

    # Delega l'estrazione della traccia audio al modulo applicativo
    audio_path = extract_audio(str(video_path))
    
    # Invoca l'agente trascrittore (ASR) per analizzare il sample audio
    transcription_data = agents["transcriber"].transcribe(str(audio_path))

    return {"filename": file.filename, "transcription": transcription_data}


@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    """
    Endpoint delegato all'orchestrazione del componente di Traduzione.
    Applica pattern architetturali per mantenere il disaccoppiamento esplicito (Decoupled Pipeline) 
    tra la trascrizione pregressa e la sintesi successiva.
    """
    # Inizializza l'agente di traduzione associandolo alla lingua target desiderata
    translator = TranslationAgent(target_language=request.target_language)
    
    # [PATTERN: Input Normalization]
    # Normalizza la struttura polimorfica in ingresso a un unico formato gestibile uniformemente (list[dict]).
    # Questa standardizzazione previene blocchi sequenziali ad alto throughput (Iterazione Bloccante).
    if isinstance(request.text, list):
        # Mantiene la composizione strutturale pre-calcolata originata dal modulo ASR
        chunks_to_process = request.text
    else:
        # Wrap del payload in un chunk artificiale per un'elaborazione uniforme
        chunks_to_process = [{"text": request.text}]

    # [PATTERN: Batch Orchestration / Unified Bulk Call]
    # Delega la logica iterativa e di mantenimento contesto all'Agente traduttore, abbattendo la latenza cumulativa.
    translated_results = translator.translate(chunks_to_process)
    
    # [PATTERN: Response Hydration & Data Reassembly]
    # Re-idratazione del payload: consolida i testi appena tradotti all'interno delle strutture 
    # di metadati originali (es. marcatori temporali) prodotte dal layer ASR.
    if isinstance(request.text, list):
        translated_chunks = []
        # Combina i segmenti originali coi nuovi risultati mantenendo l'ordinamento topologico temporale O(n)
        for original_chunk, new_text in zip(request.text, translated_results):
            new_chunk = original_chunk.copy()
            new_chunk["text"] = new_text
            translated_chunks.append(new_chunk)
            
        return {"original_text": request.text, "translated_text": translated_chunks}
    
    # Restituisce una striga piana se l'input originario non era vettorializzato in segmenti
    return {"original_text": request.text, "translated_text": translated_results[0]}


def process_dubbing_task(job_id: str, request: DubbingRequest):
    """
    Worker node asincrono isolato dal main-thread HTTP.
    Gestisce l'intera pipeline di computazione pesante: Data Parsing -> Generazione TTS -> Video Muxing.
    
    Aggiorna sincronicamente lo stato globale in `job_store` per consentire le operazioni di long-polling.
    
    Args:
        job_id (str): UUID primario per istanziare l'esecuzione del job.
        request (DubbingRequest): DTO contenente i riferimenti dei media e dei testi traslati.
    """
    try:
        # Inizializza la metrica di completamento del task nello storage condiviso
        job_store[job_id] = {"status": "processing", "progress": 0, "stage": "initializing"}
        
        def update_progress(progress_val: int, stage_label: str):
            """Funzione closure di callback inviata ai moduli AI per il tracciamento real-time."""
            if job_id in job_store:
                job_store[job_id].update({"progress": progress_val, "stage": stage_label})

        # Risoluzione predittiva dei percorsi sul file system temporaneo
        video_path = TEMP_DIR / request.video_filename
        
        # Assume come traccia reference per il voice cloning l'audio raw estratto preliminarmente durante la trascrizione
        reference_audio_path = TEMP_DIR / f"{Path(request.video_filename).stem}.wav"
        
        text_to_speak = request.translated_text
        
        # Routing condizionale di formattazione del JSON in ingresso a beneficio del modulo TTS
        try:
            parsed_data = json.loads(text_to_speak) if isinstance(text_to_speak, str) else text_to_speak
            if isinstance(parsed_data, list):
                # Estrae le componenti testuali e scarta eventuali bounding-box estranei generati da moduli antecedenti
                text_to_speak = " ".join([
                    item.get("text", "") 
                    for item in parsed_data 
                    if isinstance(item, dict) and "text" in item
                ])
        except Exception:
            # Fallback generico per elaborare la cache bypassando il parser strict
            pass

        # Genera un audio clonato (synthetic voice) appoggiandosi ai modelli TTS integrati
        dubbed_audio_path = agents["synthesizer"].generate_audio(
            text=text_to_speak,
            target_language=request.target_language,
            reference_audio_path=str(reference_audio_path),
            progress_callback=update_progress
        )

        update_progress(90, "merging_video")
        
        # Validazione strutturale esplicita per impedire il merge su un file audio non valido
        if dubbed_audio_path.startswith("[ERRORE"):
            raise ValueError(f"Fallimento riscontrato nel modulo TTS: {dubbed_audio_path}")

        # Costruisce il nome dell'artefatto video di destinazione (sink artifact)
        final_video_filename = f"final_{request.target_language}_{request.video_filename}"
        final_video_path = TEMP_DIR / final_video_filename

        # Fonde asincronamente flussi dati (Video Origin + Synthetic Audio) appoggiandosi a wrapper FFMPEG  
        merge_audio_video(
            video_path=str(video_path),
            audio_path=dubbed_audio_path,
            output_path=str(final_video_path)
        )
        
        # Consolida e conclude il tracing del job nello store in-memory in caso di run immacolata
        job_store[job_id].update({
            "status": "completed",
            "result": {"final_video": final_video_filename}
        })
        
    except Exception as e:
        # Interrompe l'operazione segnalando le eccezioni catturate al livello di astrazione superiore
        job_store[job_id].update({
            "status": "failed",
            "error": str(e)
        })

@app.post("/api/dub", status_code=status.HTTP_202_ACCEPTED)
async def generate_dubbing(request: DubbingRequest, background_tasks: BackgroundTasks):
    """
    Endpoint di ingestione di compiti compute-heavy (doppiaggio multimediale). 
    Prende in affido la richesta, alloca un BackgroundTask e disaccoppia la computazione dalla chiamata REST.
    Restituisce un Ticket UUID conforme all'idioma async 202 Accepted.
    """
    # Genera un identificativo crittograficamente univoco per la transazione
    job_id = str(uuid4())
    
    # Pre-riserva lo scope del task nel dictionary in maniera sincrona per evitare lookup mancanti alle chiamate immediate dal front-end
    job_store[job_id] = {
        "status": "pending",
        "progress": 0,
        "stage": "queued",
        "result": None,
        "error": None
    }
    
    # Pone in esecuzione il batch job threadless
    background_tasks.add_task(process_dubbing_task, job_id, request)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Il processo di doppiaggio è stato accodato. Usa l'attributo job_id per monitorarne progressivamente lo stato via polling."
    }


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Meccanismo di streaming e payload byte-serving per recuperare i media generati.
    I FileResponse FastAPI evitano memory leak serializzando gradualmente blocchi binari al consumer HTTP.
    """
    file_path = TEMP_DIR / filename

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Endpoint del protocollo di polling (Status Endpoint).
    Permette al client-side di effettuare ping ciclici per verificare lo stadio avanzivo di worker lenti (es. modulo TTS).
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job specificato non trovato in memoria temporanea.")
    
    return job_store[job_id]

