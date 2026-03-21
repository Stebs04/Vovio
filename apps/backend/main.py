
# --- Imports Standard e Third-Party ---
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse

# --- Imports Configurazione e Utility ---
from config import TEMP_DIR
from utils.video_processing import extract_audio, merge_audio_video

# --- Imports Agenti AI ---
from agents.transcriber import TranscriptionAgent
from agents.translator import TranslationAgent
from agents.synthesizer import SynthesizerAgent

# --- Inizializzazione App e Servizi ---
app = FastAPI(
    title="Vovio Backend",
    description="API per trascrizione e traduzione video automatizzata",
    version="0.1.0"
)

# Istanza globale degli agenti AI (caricati all'avvio per ottimizzare le performance)
transcriber_agent = TranscriptionAgent()
synthesizer_agent = SynthesizerAgent()

class TranslationRequest(BaseModel):
    """
    Modello Pydantic per la richiesta di traduzione.
    Definisce la struttura attesa per il corpo della richiesta JSON.
    """
    text: str              # Il testo originale da tradurre
    target_language: str   # Il codice della lingua di destinazione (es. "ita", "esp")

class DubbingRequest(BaseModel):
    """
    Modello per la richiesta di doppiaggio video.
    """
    video_filename: str    # Nome del file video caricato precedentemente (già presente in TEMP_DIR)
    translated_text: str   # Testo tradotto da sintetizzare
    target_language: str   # Lingua target per la sintesi vocale


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
async def transcribe_video(file: UploadFile = File(...)):
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


@app.post("/api/dub")
async def generate_dubbing(request: DubbingRequest):
    """
    Endpoint per la generazione del video doppiato.
    
    Orchestra il processo di sintesi vocale e muxing audio/video:
    1. Recupera i percorsi dei file video sorgente e audio di riferimento.
    2. Genera la nuova traccia audio doppiata (TTS).
    3. Fonde il video originale con il nuovo audio.
    
    Returns:
        JSON con stato e nome del file video finale generato.
    """
    # 1. Setup dei percorsi file
    # Si assume che il file video e l'audio estratto (usato come reference per la voce) esistano già
    video_path = TEMP_DIR / request.video_filename
    
    # Il file audio di riferimento serve per clonare la voce (Speaker Voice Cloning)
    reference_audio_path = TEMP_DIR / f"{Path(request.video_filename).stem}.wav"
    
    # 2. Generazione Audio (TTS)
    # Sintetizza il testo tradotto nella lingua target, clonando la voce originale
    dubbed_audio_path = synthesizer_agent.generate_audio(
        text=request.translated_text, 
        target_language=request.target_language,
        reference_audio_path=str(reference_audio_path)
    )
    
    # 3. Mixing Audio/Video
    # Crea il file finale combinando video originale e nuovo audio
    final_video_filename = f"final_{request.target_language}_{request.video_filename}"
    final_video_path = TEMP_DIR / final_video_filename
    
    merge_audio_video(
        video_path=str(video_path), 
        audio_path=dubbed_audio_path, 
        output_path=str(final_video_path)
    )
    
    return {
        "status": "success", 
        "final_video": final_video_filename
    }


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Endpoint per il download dei file processati.
    
    Permette al frontend di scaricare i video finali o altri artefatti dalla directory temporanea.

    Args:
        filename (str): Nome del file da scaricare (presente in TEMP_DIR).

    Returns:
        FileResponse: Il file richiesto in stream, con media_type "video/mp4".
    """
    # Costruzione sicura del percorso file
    # TODO: In produzione, implementare controlli di sicurezza (path traversal prevention)
    file_path = TEMP_DIR / filename
    
    # Restituzione del file come stream binario
    # media_type impostato su video/mp4, da generalizzare se si scaricano altri tipi
    return FileResponse(
        path=str(file_path), 
        media_type="video/mp4", 
        filename=filename
    )