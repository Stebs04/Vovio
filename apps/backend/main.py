
import json
# Importa FastAPI e i tipi necessari per gestire endpoint e upload file.
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, status
# Importa BaseModel per validare automaticamente i payload JSON in ingresso.
from pydantic import BaseModel
# Importa Path per manipolare percorsi filesystem in modo robusto e portabile.
from pathlib import Path
# Importa la risposta file-streaming per consentire il download di file elaborati.
from fastapi.responses import FileResponse
# Importa il middleware CORS per permettere chiamate dal frontend.
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

# Importa la directory temporanea condivisa per gli artefatti di processo.
from config import TEMP_DIR
# Importa le utility di estrazione audio e fusione audio/video basate su ffmpeg.
from utils.video_processing import extract_audio, merge_audio_video

# Importa l'agente incaricato della trascrizione automatica.
from agents.transcriber import TranscriptionAgent
# Importa l'agente incaricato della traduzione testuale.
from agents.translator import TranslationAgent
# Importa l'agente incaricato della sintesi vocale (TTS).
from agents.synthesizer import SynthesizerAgent

job_store = {}

# Crea l'applicazione FastAPI con metadati utili a documentazione e versionamento.
app = FastAPI(
    # Imposta il titolo esposto nella documentazione OpenAPI.
    title="Vovio Backend",
    # Descrive sinteticamente lo scopo del servizio backend.
    description="API per trascrizione e traduzione video automatizzata",
    # Definisce la versione corrente dell'API.
    version="0.1.0"
)

# Registra il middleware CORS per abilitare le richieste dal client web locale.
app.add_middleware(
    # Specifica la classe middleware da applicare alla pipeline HTTP.
    CORSMiddleware,
    # Consente richieste soltanto dall'origine frontend in sviluppo.
    allow_origins=["http://localhost:3000"],
    # Permette invio di cookie/header credenziali cross-origin.
    allow_credentials=True,
    # Consente tutti i metodi HTTP (GET, POST, ecc.) per semplicità in sviluppo.
    allow_methods=["*"],
    # Consente tutti gli header HTTP personalizzati inviati dal client.
    allow_headers=["*"],
)

# Inizializza una sola volta l'agente di trascrizione per evitare costi ripetuti a runtime.
transcriber_agent = TranscriptionAgent()
# Inizializza una sola volta l'agente di sintesi per ridurre la latenza delle richieste.
synthesizer_agent = SynthesizerAgent()


class TranslationRequest(BaseModel):
    """
    Modello Pydantic per la richiesta di traduzione.
    Definisce la struttura attesa per il corpo della richiesta JSON.
    """
    # Architettura: Usiamo la Type Union (|) per permettere a Pydantic di accettare
    # sia stringhe semplici che le liste di dizionari generate da Whisper.
    text: str | list       
    target_language: str


# Definisce il modello dati della richiesta di doppiaggio video.
class DubbingRequest(BaseModel):
    # Nome del file video già caricato nella cartella temporanea.
    video_filename: str
    # Testo tradotto che verrà convertito in parlato.
    translated_text: str | list
    # Codice della lingua di destinazione per la sintesi vocale.
    target_language: str


# Espone un endpoint di health-check per verificare rapidamente lo stato del backend.
@app.get("/")
# Definisce una coroutine asincrona che restituisce metadati di stato servizio.
async def get_status():
    # Restituisce un dizionario serializzato in JSON con stato e versione.
    return {
        # Indica che il servizio risulta operativo.
        "status": "operational",
        # Identifica il nome logico dell'applicazione.
        "app": "vovio",
        # Comunica la versione API esposta.
        "version": "0.1.0"
    }


# Espone l'endpoint che riceve un video e produce la relativa trascrizione.
@app.post("/api/transcribe")
# Definisce la funzione asincrona che accetta un file multipart obbligatorio.
async def transcribe_video(file: UploadFile = File(...)):
    # Calcola il percorso di salvataggio temporaneo del video caricato.
    video_path = TEMP_DIR / file.filename
    # Apre il file destinazione in modalità binaria di scrittura.
    with open(video_path, "wb") as buffer:
        # Legge il contenuto upload asincrono e lo scrive sul filesystem locale.
        buffer.write(await file.read())

    # Estrae la traccia audio dal video per poterla inviare al motore di ASR.
    audio_path = extract_audio(str(video_path))

    # Esegue la trascrizione automatica passando il percorso audio estratto.
    transcription_data = transcriber_agent.transcribe(str(audio_path))

    # Restituisce filename e payload di trascrizione al client chiamante.
    return {"filename": file.filename, "transcription": transcription_data}


@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    """
    Endpoint per la traduzione del testo.
    """
    translator = TranslationAgent(target_language=request.target_language)
    
    # Data Normalization: Se il payload in ingresso è la lista di segmenti di Whisper,
    # la serializziamo in una stringa JSON prima di iniettarla nel prompt del LLM, 
    # affinché il modello ne preservi la struttura temporale.
    payload = request.text if isinstance(request.text, str) else json.dumps(request.text)
    
    translated_text = translator.translate(payload)
    
    return {"original_text": request.text, "translated_text": translated_text}


# Espone l'endpoint che genera un nuovo video doppiato con audio sintetizzato.
@app.post("/api/dub")
# Definisce la funzione asincrona che orchestra sintesi vocale e merge finale.
async def generate_dubbing(request: DubbingRequest):
    # Costruisce il percorso del video sorgente a partire dal nome file ricevuto.
    video_path = TEMP_DIR / request.video_filename

    # Deriva il nome del file WAV di riferimento vocale dal nome base del video.
    reference_audio_path = TEMP_DIR / f"{Path(request.video_filename).stem}.wav"

    text_to_speak = request.translated_text
    try:
        if isinstance(text_to_speak, str):
            parsed_data = json.loads(text_to_speak)
        else:
            parsed_data = text_to_speak

        if isinstance(parsed_data, list):
            text_to_speak= " ".join([item ["text"] for item in parsed_data if "text" in item])
    except:
        pass

    # Genera l'audio doppiato usando testo tradotto, lingua target e timbro di riferimento.
    dubbed_audio_path = synthesizer_agent.generate_audio(
        # Passa il testo da convertire in voce.
        text=text_to_speak,
        # Passa il codice lingua per il motore TTS.
        target_language=request.target_language,
        # Passa il percorso audio usato per il voice cloning.
        reference_audio_path=str(reference_audio_path)
    )
    if dubbed_audio_path.startswith("[ERRORE"):
        raise HTTPException(status_code=500, detail=dubbed_audio_path)

    # Costruisce il nome del file finale includendo lingua e nome originale.
    final_video_filename = f"final_{request.target_language}_{request.video_filename}"
    # Costruisce il percorso completo del file video finale nella cartella temporanea.
    final_video_path = TEMP_DIR / final_video_filename

    # Esegue il merge tra video originale e nuova traccia audio doppiata.
    merge_audio_video(
        # Fornisce il percorso del video sorgente.
        video_path=str(video_path),
        # Fornisce il percorso dell'audio sintetizzato.
        audio_path=dubbed_audio_path,
        # Fornisce il percorso di output del video finale.
        output_path=str(final_video_path)
    )

    # Restituisce esito positivo e nome del file generato.
    return {
        # Flag semantico di completamento processo.
        "status": "success",
        # Nome del file finale scaricabile dal frontend.
        "final_video": final_video_filename
    }


# Espone l'endpoint di download per file generati durante la pipeline.
@app.get("/api/download/{filename}")
# Definisce la funzione asincrona che restituisce lo stream del file richiesto.
async def download_file(filename: str):
    # Costruisce il path assoluto/relativo nella directory temporanea controllata.
    file_path = TEMP_DIR / filename

    # Restituisce il file in streaming impostando media type video MP4.
    return FileResponse(
        # Percorso effettivo del file da inviare al client.
        path=str(file_path),
        # Tipo MIME usato dal browser per interpretare correttamente il contenuto.
        media_type="video/mp4",
        # Nome file proposto al client nel download.
        filename=filename
    )