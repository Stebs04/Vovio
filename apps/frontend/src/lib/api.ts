import { apiClient } from "./apiClient";
// DTOs importati per la validazione statica dei payload di rete
import { 
    TranslationRequest, 
    TranslationResponse, 
    DubbingRequest, 
    DubbingResponse, 
    TranscriptionResponse, 
    JobStatusResponse
} from "@/types/api";

/**
 * Inoltra la richiesta di traduzione testuale al servizio backend.
 * 
 * @param data - Payload contenente il testo sorgente e la lingua di destinazione.
 * @returns {Promise<TranslationResponse>} Risultato elaborato dall'agente LLM.
 */
export const translateText = async (data: TranslationRequest): Promise<TranslationResponse> => {
    const response = await apiClient.post<TranslationResponse>('/api/translate', data);
    return response.data;
};

/**
 * Inizializza asincronamente la pipeline di sintesi vocale e doppiaggio video.
 * L'operazione restituisce un job_id per abilitare il successivo polling dello stato.
 * 
 * @param data - Target del doppiaggio e parametri di configurazione del task.
 * @returns {Promise<DubbingResponse>} Dettagli di conformità della richiesta e identificativo del job.
 */
export const generateDubbing = async (data: DubbingRequest): Promise<DubbingResponse> => {
    const response = await apiClient.post<DubbingResponse>('/api/dub', data);
    return response.data;
};

/**
 * Esegue l'upload di un media video per l'estrazione della traccia audio e la conseguente trascrizione vocale.
 * Gestisce l'incapsulamento del binario su protocollo multipart/form-data.
 * 
 * @param videoFile - L'istanza File nativa indicata in upload.
 * @returns {Promise<TranscriptionResponse>} Trascrizione strutturata emessa dal motore ASR.
 */
export const transcribeVideo = async (videoFile: File): Promise<TranscriptionResponse> => {
    const formData = new FormData();
    formData.append('file', videoFile);

    const response = await apiClient.post<TranscriptionResponse>('/api/transcribe', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });

    return response.data;
};

/**
 * Verifica lo stato di avanzamento di elaborazioni di backend computazionalmente onerose.
 * Concepito specificatamente per flussi di short-polling lato client.
 * 
 * @param jobId - L'UUID referenziale del task asincrono allocato in avvio.
 * @returns {Promise<JobStatusResponse>} L'istantanea valutativa dello stadio di maturazione del processo.
 */
export const checkJobStatus = async (jobId: string): Promise<JobStatusResponse> =>{
    const response = await apiClient.get<JobStatusResponse>(`/api/jobs/${jobId}`);
    return response.data;
}