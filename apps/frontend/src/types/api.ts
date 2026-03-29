/**
 * Payload della richiesta di traduzione.
 * Rappresenta i parametri inviati al backend per la traduzione di un testo specifico.
 */
export interface TranslationRequest {
    /** Il testo sorgente da tradurre (può essere una stringa normale o JSON strutturato) */
    text: string
    /** Il codice locale della lingua di destinazione (es. "it", "en") */
    target_language: string
}

/**
 * Payload della risposta di traduzione.
 * Restituisce il risultato dell'agente AI insieme al testo originale per i controlli lato UI.
 */
export interface TranslationResponse {
    /** Il blocco di testo originale sottomesso in fase di richiesta */
    original_text: string
    /** Il risultato testuale della traduzione generata dal sistema */
    translated_text: string
}

/**
 * Payload della richiesta asincrona di doppiaggio (TTS e muxing).
 * Veicola i riferimenti essenziali per inizializzare il job nel worker di backend.
 */
export interface DubbingRequest {
    /** L'identificativo del file video originale pre-caricato sul filesystem temporaneo dal client */
    video_filename: string
    /** Il contenuto testuale tradotto che il motore di sintesi vocale convertirà in audio */
    translated_text: string
    /** Il codice della lingua target impiegato per configurare il modello TTS */
    target_language: string
}

/**
 * Payload di risposta per l'inizio di un'operazione di doppiaggio.
 * Ritorna le credenziali del task (job_id) indispensabili per il polling dello stato.
 */
export interface DubbingResponse {
    /** Lo stato di presa in carico elaborativa (generalmente "accepted") */
    status: string
    /** L'identificatore univoco univoco (UUID) assegnato al processo in background */
    job_id: string
    /** Messaggio opaco descrittivo del lifecycle del task */
    message: string
}

/**
 * Payload della risposta del motore di trascrizione.
 * Raccoglie l'output dell'ASR (Automatic Speech Recognition) a partire dal flusso audio.
 */
export interface TranscriptionResponse {
    /** Il nome del file video che è stato elaborato */
    filename: string
    /** Il formato testuale completo della trascrizione estratta */
    transcription: string
}

/**
 * Payload esposto dall'endpoint di health-check sui job asincroni.
 * Consente al frontend di reagire all'avanzamento dei task di lunga durata.
 */
export interface JobStatusResponse {
    /** Discreto di macchina a stati per l'avanzamento dell'elaborazione */
    status: 'pending' | 'processing' | 'completed' | 'failed';
    /** Articolazione del risultato, valorizzata eslusivamente nello stato "completed" */
    result?: {
        /** Il nome finale del file video renderizzato, pronto per il serve o il download */
        final_video: string
    };
    /** Messaggio esplicito scatenato da una potenziale eccezione se in stato "failed" */
    error?: string;
}