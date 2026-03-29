import { useState } from 'react';
import {
     transcribeVideo, translateText, generateDubbing, checkJobStatus
} from '@/lib/api';

/**
 * Struttura dati che rappresenta lo stato globale della pipeline asincrona.
 * Modella una macchina a stati per tenere traccia dei progressi, dei payload e dei potenziali fault.
 */
export interface PipelineState {
    /** Identificatore del nodo corrente nella macchina a stati della pipeline */
    currentStep: 'IDLE' | 'TRANSCRIBING' | 'TRANSLATING' | 'DUBBING' | 'SUCCESS' | 'ERROR';
    /** Referenza locale (nativa HTML5) al file video sottoposto dall'utente */
    videoFile: File | null;
    /** Output JSON o testuale restituito dall'ASR post-elaborazione */
    transcription: string | null;
    /** Output testuale della traduzione inferita dal LLM */
    translation: string | null;
    /** Endpoint assoluto per accedere al media finale muxato per la localizzazione */
    finalVideoUrl: string | null;
    /** Traccia la percentuale di avanzamento del task di doppiaggio */
    dubbingProgress: number;
    /** Stringa descrittiva dello step attualmente in esecuzione sul backend */
    dubbingStage: string | null;
    /** Accumulatore per le stringhe di eccezione destinate alla UI */
    error: string | null;
}

const initialState: PipelineState = {
    currentStep: 'IDLE',
    videoFile: null,
    transcription: null,
    translation: null,
    finalVideoUrl: null,
    dubbingProgress: 0,
    dubbingStage: null,
    error: null,
}

/**
 * Hook custom React per la gestione del ciclo di vita della pipeline di Vovio.
 * Gestisce la persistenza in locale del flusso (Trascrizione -> Traduzione -> Doppiaggio) e le policy di riprova/polling.
 * 
 * @returns Tuple contenente l'oggetto dello stato reattivo e i controller di transizione.
 */
export const useVovioPipeline = () => {
    const [state, setState] = useState<PipelineState>(initialState);

    /**
     * Esegue il binding del media al context della pipeline.
     * 
     * @param file - Il payload multimediale da agganciare allo stream locale.
     */
    const setFile = (file: File) => {
        setState({
            ...state,
            videoFile: file
        });
    }

    /**
     * Invoca il layer di rete per estrarre la grammatica e il testo dal video aggregato.
     * 
     * @param file - Elemento opzionalmente disaccoppiato dallo stato locale, passato direttamente.
     */
    const startTranscription = async (file: File) => {
        if (!file) {
            setState({
                ...state,
                error: 'Nessun file selezionato. Impossibile avviare la trascrizione.'
            });
            return;
        }

        setState({
            ...state,
            videoFile: file,
            currentStep: 'TRANSCRIBING',
            error: null
        });

        try {
            const response = await transcribeVideo(file);
            
            setState({
                ...state,
                currentStep: 'IDLE',
                transcription: response.transcription,
            });
        } catch (error) {
            setState({
                ...state,
                currentStep: 'ERROR',
                error: 'Errore generico durante la comunicazione con il servizio ASR (Whisper).'
            });
        }
    }

    /**
     * Promuove la trascrizione in cache locale in una lingua specificata dall'user intent.
     * 
     * @param targetLanguage - Locale string della lingua target (es. 'en', 'es').
     */
    const startTranslation = async (targetLanguage: string) => {
        if (!state.transcription) {
            setState({
                ...state,
                error: "Dati di origine mancanti. Nessuna trascrizione allocata per la traduzione."
            });
            return;
        }

        setState({
            ...state,
            currentStep: 'TRANSLATING',
            error: null
        });

        try {
            const response = await translateText({
                text: state.transcription,
                target_language: targetLanguage
            });
            
            setState({
                ...state,
                currentStep: 'IDLE',
                translation: response.translated_text
            });
        } catch (error) {
            setState({
                ...state,
                currentStep: 'ERROR',
                error: 'Interruzione inaspettata durante la pipeline di traduzione del LLM.'
            });
        }
    }

    /**
     * Triggera il task di back-office intensivo per sintetizzare la voce, clonare il pitch e ricreare il media.
     * Utilizza un meccanismo di short-polling bloccante per attendere il fine ciclo (async worker resolution).
     * 
     * @param targetLanguage - Locale string configurato per il modello TTS.
     * @param videoFileName - Riferimento logico al file di spool per il backend.
     */
    const startDubbing = async (targetLanguage: string, videoFileName: string) => {
        if (!videoFileName || !state.translation) {
            setState({
                ...state,
                error: 'Impossibile risolvere il job: asset multimediali o testuali non inizializzati.'
            });
            return;
        }

        setState({
            ...state,
            currentStep: 'DUBBING',
            error: null
        });

        try {
           const initResponse = await generateDubbing({
            video_filename: videoFileName,
            translated_text: state.translation,
            target_language: targetLanguage
           });

           // Ciclo di polling asincrono per monitorare l'evoluzione della coda su Redis/Memory.
           while(true){
                const statusResponse = await checkJobStatus(initResponse.job_id);
                // Aggiorna lo stato locale con la percentuale di completamento e la fase corrente del task
                setState(prevState => ({
                    ...prevState,
                    dubbingProgress: statusResponse.progress,
                    dubbingStage: statusResponse.stage
                }))
                if( statusResponse.status === 'completed'){
                    setState({
                        ...state,
                        currentStep: 'SUCCESS',
                        finalVideoUrl: `http://localhost:8000/api/download/${statusResponse.result?.final_video}`
                    });
                    // Rilascio del runtime lock alla corretta composiszione del file.
                    break;
                } else if(statusResponse.status === 'failed'){
                    throw new Error(statusResponse.error || "Fallimento opaco del task di backend.");
                }
                
                // Sleep deterministico per prevenire l'esaurimento del Thread Pool e limitare le RPC calls (3 sec).
                await new Promise((resolve) => setTimeout(resolve, 3000));
           } 
        } catch (error) {
            setState({
                ...state,
                currentStep: 'ERROR',
                error: error instanceof Error ? error.message : "Fallimento critico nell'orchestratore del Worker video."
            });
        }
    }

    return {
        state,
        setFile,
        startTranscription,
        startTranslation,
        startDubbing
    };
}

