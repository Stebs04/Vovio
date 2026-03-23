import { apiClient } from "./apiClient";
// Importa le interfacce per la tipizzazione rigorosa di richieste e risposte
import { 
    TranslationRequest, 
    TranslationResponse, 
    DubbingRequest, 
    DubbingResponse, 
    TranscriptionResponse 
} from "@/types/api";

/**
 * Invia il testo al backend per la traduzione tramite l'Agente AI.
 * Utilizza il DTO TranslationRequest per garantire che i dati siano formattati correttamente.
 * 
 * @param data - L'oggetto contenente il testo e la lingua di destinazione.
 * @returns La risposta del server contenente sia il testo originale che quello tradotto.
 */
export const translateText = async (data: TranslationRequest): Promise<TranslationResponse> => {
    // Effettua una chiamata POST asincrona all'endpoint '/api/translate'.
    // Utilizza il generic <TranslationResponse> per indicare ad Axios che il body della risposta sarà di questo tipo.
    // Passa 'data' come payload JSON della richiesta.
    const response = await apiClient.post<TranslationResponse>('/api/translate', data);
    
    // Restituisce solo la proprietà .data della risposta Axios, che contiene il payload JSON effettivo inviato dal server.
    return response.data;
};

/**
 * Avvia il processo di doppiaggio inviando il testo tradotto e il riferimento al video.
 * Il backend orchestrerà la sintesi vocale e il muxing finale.
 * 
 * @param data - DTO contenente il nome del file video e il testo tradotto.
 * @returns Oggetto con lo stato dell'operazione e il path del video finale.
 */
export const generateDubbing = async (data: DubbingRequest): Promise<DubbingResponse> => {
    // Chiamata POST all'endpoint '/api/dub' per avviare il job di doppiaggio.
    // Anche qui tipizza la risposta attesa come <DubbingResponse>.
    const response = await apiClient.post<DubbingResponse>('/api/dub', data);
    
    // Estrae e ritorna i dati della risposta (status e path del video finale).
    return response.data;
};

/**
 * Carica un file video sul server per estrarne la trascrizione.
 * Gestisce l'upload tramite FormData, necessario per il trasferimento di file binari.
 * 
 * @param videoFile - L'oggetto File nativo del browser proveniente dall'input utente.
 * @returns La trascrizione testuale generata da Faster-Whisper.
 */
export const transcribeVideo = async (videoFile: File): Promise<TranscriptionResponse> => {
    // Istanzia un oggetto FormData, che è lo standard browser per inviare dati binari (form-data).
    const formData = new FormData();
    
    // Aggiunge il file video all'oggetto FormData con la chiave 'file' (che il backend si aspetta).
    formData.append('file', videoFile);

    // Esegue la POST verso '/api/transcribe'.
    // Passa il formData come body.
    const response = await apiClient.post<TranscriptionResponse>('/api/transcribe', formData, {
        // Configura gli header specifici per questa richiesta.
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });

    // Restituisce il payload della risposta parsato dal JSON, contenente trascrizione e nome file.
    return response.data;
};