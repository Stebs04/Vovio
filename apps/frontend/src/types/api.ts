/**
 * DTO per la richiesta di traduzione.
 * Mappa esattamente il modello Pydantic TranslationRequest del backend FastAPI.
 */
export interface TranslationRequest {
    text: string
    target_language: string
}

/**
 * DTO per la risposta dell'endpoint di traduzione.
 * Contiene sia il testo originale (per controlli di coerenza nella UI) che il risultato dell'Agente AI.
 */

export interface TranslationResponse{
    original_text: string
    translated_text: string
}

/**
 * DTO per la richiesta di doppiaggio.
 * Fornisce al backend i riferimenti al file video temporaneo e il testo tradotto da sintetizzare.
 */
export interface DubbingRequest{
    video_filename: string
    translated_text: string
    target_language: string
}

/**
 * DTO per la risposta di doppiaggio.
 * Contiene lo stato dell'operazione e il nome del file video muxato (H.264/AAC) pronto per il download.
 */
export interface DubbingResponse {
    status: string
    final_video: string
}

/**
 * DTO per la risposta dell'endpoint di trascrizione.
 * Restituisce il testo estratto tramite Faster-Whisper e il nome del file originale.
 */
export interface TranscriptionResponse {
    filename: string
    transcription: string
}