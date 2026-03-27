import { useState } from 'react';
import {
     transcribeVideo, translateText, generateDubbing 
    } from '@/lib/api';

/**
 * Rappresenta lo stato della pipeline di elaborazione video.
 * Tiene traccia della fase corrente, dei dati di input/output e di eventuali errori.
 */
export interface PipelineState {
    /** La fase attuale del flusso di lavoro. */
    currentStep: 'IDLE' | 'TRANSCRIBING' | 'TRANSLATING' | 'DUBBING' | 'SUCCESS' | 'ERROR';
    /** Il file video sorgente caricato dall'utente. */
    videoFile: File | null;
    /** Il testo della trascrizione estratto dal video. */
    transcription: string | null;
    /** Il testo tradotto generato dalla trascrizione. */
    translation: string | null;
    /** L'URL del video finale doppiato. */
    finalVideoUrl: string | null;
    /** Messaggio di errore in caso di fallimento della pipeline. */
    error: string | null;
}

/**
 * Stato iniziale della pipeline.
 * Inizia in stato IDLE senza dati caricati.
 */
const initialState: PipelineState = {
    currentStep: 'IDLE',
    videoFile: null,
    transcription: null,
    translation: null,
    finalVideoUrl: null,
    error: null,
}

/**
 * Hook personalizzato per gestire la pipeline di elaborazione video Vovio.
 * Gestisce le transizioni di stato tra le fasi di trascrizione, traduzione e doppiaggio.
 */
export const useVovioPipeline = () => {
    // Inizializza lo stato reattivo per gestire il ciclo di vita della pipeline
    const [state, setState] = useState<PipelineState>(initialState);

    /**
     * Salva il file video selezionato dall'utente nello stato locale.
     */
    const setFile = (file: File) => {
        // Aggiorna lo stato mantenendo le proprietà esistenti e sovrascrivendo il file video
        setState({
            ...state,
            videoFile: file
        })
    }

    /**
     * Avvia il processo asincrono di trascrizione.
     * Cambia lo stato per indicare il caricamento e chiama il Service Layer API.
     */
    const startTranscription = async (file:File) => {
        // VALIDAZIONE: Verifica preliminare per assicurarsi che un file sia stato caricato
        if (!file) {
            // Se nessun file è presente, imposta un errore nello stato e interrompe
            setState({
                ...state,
                error: 'Nessun file selezionato. Impossibile avviare la trascrizione.'
            });
            return;
        }

        // SETUP: Aggiorna lo stato per indicare l'inizio della trascrizione (loading spinner)
        setState({
            ...state,
            videoFile:file,
            currentStep: 'TRANSCRIBING',
            error: null // Azzera eventuali errori precedenti
        })

        // ESECUZIONE: Avvia la pipeline e gestisce la Graceful Degradation in caso di fault di rete
        try {
            // Esegue la chiamata all'API di trascrizione passando il file video
            const response = await transcribeVideo(file);
            
            // SUCCESSO: Aggiorna lo stato con la trascrizione ricevuta dal backend
            setState({
                ...state,
                currentStep: 'IDLE', // Riporta lo stato a IDLE per l'azione successiva
                transcription: response.transcription,
            })
        } catch (error) {
            // ERRORE: Gestisce le eccezioni durante la comunicazione con il servizio Whisper
            setState({
                ...state,
                currentStep: 'ERROR',
                error: 'Errore durante la comunicazione con Whisper'
            })
        }
    }

    /**
     * Avvia il processo di traduzione del testo trascritto.
     * 
     * @param targetLanguage - Il codice della lingua di destinazione (es. 'en', 'es', 'fr').
     */
    const startTranslation = async (targetLanguage: string) => {
        // VALIDAZIONE: Verifica che la trascrizione sia disponibile come input
        if (!state.transcription) {
            setState({
                ...state,
                error: "Nessuna trascrizione presente. Impossibile avviare la traduzione."
            });
            return;
        }

        // SETUP: Imposta lo stato su TRANSLATING per feedback visivo all'utente
        setState({
            ...state,
            currentStep: 'TRANSLATING',
            error: null
        });

        // ESECUZIONE: Invoca il servizio di traduzione
        try {
            const response = await translateText({
                text: state.transcription,
                target_language: targetLanguage
            });
            
            // SUCCESSO: Memorizza il testo tradotto nello stato
            setState({
                ...state,
                currentStep: 'IDLE',
                translation: response.translated_text
            });
        } catch (error) {
            // ERRORE: Notifica il fallimento del processo di traduzione
            setState({
                ...state,
                currentStep: 'ERROR',
                error: 'Si è verificato un errore durante la traduzione dei sottotitoli.'
            });
        }
    }

    /**
     * Avvia il processo di doppiaggio (dubbing) del video originale.
     * Utilizza il testo tradotto per generare una nuova traccia audio sincronizzata.
     * 
     * @param targetLanguage - La lingua in cui doppiare il video.
     */
    const startDubbing = async (targetLanguage: string) => {
        // VALIDAZIONE: Verifica la presenza di tutti gli asset necessari (video e traduzione)
        if (!state.videoFile || !state.translation) {
            setState({
                ...state,
                error: 'File video o traduzione mancanti. Impossibile procedere con il doppiaggio.'
            });
            return;
        }

        // SETUP: Indica l'avvio del processo di generazione audio/video
        setState({
            ...state,
            currentStep: 'DUBBING',
            error: null // Reset degli errori
        });

        // ESECUZIONE: Richiede al backend la generazione del video doppiato
        try {
            const response = await generateDubbing({
                video_filename: state.videoFile.name, // Riferimento al nome del file
                translated_text: state.translation,
                target_language: targetLanguage
            });

            // SUCCESSO: Salva l'URL del video finale per la visualizzazione/download
            setState({
                ...state,
                currentStep: 'SUCCESS',
                finalVideoUrl: response.final_video
            });
        } catch (error) {
            // ERRORE: Gestione del fallimento nella generazione del video
            setState({
                ...state,
                currentStep: 'ERROR',
                error: "Impossibile generare il video doppiato. Riprovare più tardi."
            });
        }
    }

    // EXPORT: Restituisce state e funzioni ai componenti React
    return {
        state,
        setFile,
        startTranscription,
        startTranslation,
        startDubbing
    };
}

