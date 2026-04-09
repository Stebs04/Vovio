// Importiamo l'hook nativo di React per la gestione reattiva dello stato allocato nel componente.
import { useState } from 'react';
// Importiamo i wrapper delle chiamate API Axios/Fetch che incapsulano la logica HTTP verso il backend FastAPI.
import {
     transcribeVideo, translateText, generateDubbing, checkJobStatus
} from '@/lib/api';

// Definizione formale del contratto tipizzato (State Machine) che descrive lo stato dell'intero processo.
// L'uso di una macchina a stati finiti (currentStep) previene transizioni non valide nella logica della UI.
export interface PipelineState {
    // Enumerazione ristretta per tracciare lo step esecutivo univoco del workflow asincrono.
    currentStep: 'IDLE' | 'TRANSCRIBING' | 'TRANSLATING' | 'DUBBING' | 'SUCCESS' | 'ERROR';
    // Puntatore in memoria al blob del file video sorgente caricato dal client utente.
    videoFile: File | null;
    // Payload testuale (o dataset Whisper strutturato) derivato dalla fase di estrazione audio (ASR).
    transcription: string | null;
    // Stringa tradotta (o dataset re-idratato) in uscita dal motore LLM semantico per il target language.
    translation: string | null;
    // Endpoint URL assoluto per prelevare e streammare nel player UI il file finale renderizzato.
    finalVideoUrl: string | null;
    // Rateo percentuale (0-100) per aggiornare progress bar UI nel long-polling del render TTS/Mux.
    dubbingProgress: number;
    // Etichetta diagnostica logica inviata dal cluster backend (es: "merging_video", "synthesizing").
    dubbingStage: string | null;
    // Stack trace informativo in caso di fallback logico da visualizzare nei toast/banner di avviso.
    error: string | null;
}

// Allocazione costante di un oggetto freezing state per inizializzazione rapida, evitando allocazioni
// pendenti superflue per il runtime renderer, standardizzando il flush/reset della factory di stato.
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

// Implementazione dell'Hook Custom di React (Facade Pattern e BLoC). 
// Disaccoppia la business logic intensiva (API e states) dal DOM presentazionale dei container.
export const useVovioPipeline = () => {
    // Inizializzazione dello stato de-strutturato reattivo con inferenza di tipo controllata dalla interface proxy.
    const [state, setState] = useState<PipelineState>(initialState);

    // Metodo mutator esplicito puro per allocare asincronamente nel Context form locale il media BLOB iniettato input buffer.
    const setFile = (file: File) => {
        // Approccio callback-driven funzionale: iniettiamo una clousure nel setState per isolarci dai batch update async 
        // ed evitare fenomeni di corsa (race-conditions) e data curruption della state-map limit memory allocate.
        setState(prevState => ({
            ...prevState,
            videoFile: file
        }));
    }

    // Task orchestratore asincrono della computazione pipeline ASR (Automatic Speech Recognition endpoint wrapper trigger).
    const startTranscription = async (file: File) => {
        // Guard clause diagnostica: intercetta e blocca invoke logicial non sanitizzata con param injection mancante / undefined ptr.
        if (!file) {
            setState(prevState => ({
                ...prevState,
                error: 'Nessun file selezionato. Impossibile avviare la trascrizione.'
            }));
            // Short-circuit logico e rilascio anticipato per impedire IO calls upstream superflue bloccanti event thread main pool limit alloc pass.
            return;
        }

        // Mutation state proattiva (Optimistic update pattern limit): attiva global loading flag 'TRANSCRIBING' bloccando interazioni incrociate parallele.
        setState(prevState => ({
            ...prevState,
            videoFile: file,
            currentStep: 'TRANSCRIBING',
            error: null
        }));

        try {
            // Riserva thread IO bound. Rende il processo awaitable in sospensione asincrona JS event loop locale in attesa Promise fullfill fetch call target limit.
            const response = await transcribeVideo(file);
            
            // Consolida operativamente output model backend in layer status e libera blocco logico GUI passando stato su proxy ready status trigger re-render cycle mount limit.
            setState(prevState => ({
                ...prevState,
                currentStep: 'IDLE',
                transcription: response.transcription,
            }));
        // Exception filter default catch route struct: intercetta fault timeout, gateway 5xx proxy pass o proxy parser internal break log struct base.
        } catch (error) {
            // Notifica asincrona dello snapshot UI human-readable per display toast ed invalidamento flag di stato fall-off su fail hard-coded route log UI state.
            setState(prevState => ({
                ...prevState,
                currentStep: 'ERROR',
                error: 'Errore generico durante la comunicazione con il servizio ASR (Whisper).'
            }));
        }
    }

    // Trigger action asincrona proxy HTTP limit access pass execution al backend per il modulo Translator (NLP LLM inference base pipeline task pass parameter language node route alloc struct).
    const startTranslation = async (targetLanguage: string) => {
        // Validation flow limit check: accerta dipendenze in sequenza temporale logica. Il nodo NLP rifiuta esecuzione se node ASR upstream buffer reference local pointer risulta de reference nullo o vuoto.
        if (!state.transcription) {
            setState(prevState => ({
                ...prevState,
                error: "Dati di origine mancanti. Nessuna trascrizione allocata per la traduzione."
            }));
            // Trunk escape logico per salvare cycle operation event base thread limit scope drop run out struct boundary locale null reference target block.
            return;
        }

        // Aggiorna event stack pointer UI limit 'TRANSLATING' costringendo un redraw flush dell'avanzamento visuale GUI invalidando vecchi alloc reference timeout block memory proxy drop log info base stack tree run limit locale pass event frame array struct point mount local state memory.
        setState(prevState => ({
            ...prevState,
            currentStep: 'TRANSLATING',
            error: null
        }));

        try {
            // Esecuzione factory proxy fetch request per trasmettere target parameter locale pass e buffer transcritto raw text struct al wrapper API proxy client endpoint translation node proxy call HTTP fetch wrapper pass local return struct payload payload data boundary data transfer type.
            const response = await translateText({
                text: state.transcription,
                target_language: targetLanguage
            });
            
            // Appende nel target object struct locale pass la mutazione e ri-monta state proxy ready log handler status per l'uso immediato successivo della macro routine.
            setState(prevState => ({
                ...prevState,
                currentStep: 'IDLE',
                translation: response.translated_text
            }));
        // Boundary limit timeout catch exception hook limit local API upstream fault network struct JSON parser drop fail log proxy mount local node.
        } catch (error) {
            setState(prevState => ({
                ...prevState,
                currentStep: 'ERROR',
                error: 'Interruzione inaspettata durante la pipeline di traduzione del LLM.'
            }));
        }
    }

    // Job executor asincrono computazionalmente esigente: Avvia task e istituisce routine temporale d'interrogazione proxy polling limit al server per restituire feedback visivo proxy progress task completion locale TTS alloc and FFmpeg layer mux pass data limit task struct worker locale UUID polling limit state proxy mount event.
    const startDubbing = async (targetLanguage: string, videoFileName: string) => {
        // Validation handler. Invalida ed appende errore drop se proxy parameters limit e testo originato LLM upstream mount buffer son assenti/corrotti log data locale.
        if (!videoFileName || !state.translation) {
            setState(prevState => ({
                ...prevState,
                error: 'Impossibile risolvere il job: asset multimediali o testuali non inizializzati.'
            }));
            return;
        }

        // Mutation status drop boot alloc proxy: innesca il current step mount DUBBING, flusha l'avanzamento e prepara event GUI bar loop tracker per sync rate alloc locale state drop polling.
        setState(prevState => ({
            ...prevState,
            currentStep: 'DUBBING',
            dubbingProgress: 0,
            dubbingStage: null,
            error: null
        }));

        try {
           // Initialization job pass task executor HTTP 202 local submit proxy wrapper pass params payload dispatch alloc. Restituisce ticket pass JWT task handle UUID buffer local info struct job limit proxy endpoint trigger.
           const initResponse = await generateDubbing({
            video_filename: videoFileName,
            translated_text: state.translation,
            target_language: targetLanguage
           });

           // Infinite loop logico di monitoraggio asincrono (Long Polling implement proxy locale wrapper async await pattern) per disaccoppiare blocco rendering base single sync array limit hook process limit pass interval fetch proxy boundary.
           while(true){
                // Interroga REST proxy log status call alloc con JWT token handle payload tracker limit mount.
                const statusResponse = await checkJobStatus(initResponse.job_id);
                
                // Branch 1: Controllo completamento task lifecycle upstream layer endpoint done pass limit drop struct pass mount true valid.
                if(statusResponse.status === 'completed'){
                    // Quando è completato, batch mutator proxy per agglomerare tutti proxy update limit locale: max out percentage limit bar struct update target source locale download final pointer alloc e flush proxy ready flag base render pass valid hook cycle mount update data structure source node payload return end hook point drop alloc locale pointer state root instance run struct.
                    setState(prevState => ({
                        ...prevState,
                        dubbingProgress: 100,
                        dubbingStage: statusResponse.stage,
                        currentStep: 'SUCCESS',
                        // Format resource URI loc proxy mount fetch HTTP client stream download limit alloc node handler server host port local backend node access pass stream.
                        finalVideoUrl: `http://localhost:8000/api/download/${statusResponse.result?.final_video}`
                    }));
                    // Taglia il loop d'attaccamento thread local alloc ed elimina GC worker loop pointer limit reference base while mount array pointer timeout.
                    break;
                // Branch 2: Proxy Backend signal kill task failure o process fault exception struct message mount response log array limit payload info exception fallback handler JS node root trigger stack alloc.
                } else if(statusResponse.status === 'failed'){
                    // Forza sollevamento eccezione root native JS proxy e de-routine locale stack handler string mount fall info upstream proxy limit array info backend custom root pass payload JSON node data loc.
                    throw new Error(statusResponse.error || "Fallimento opaco del task di backend.");
                // Branch 3: Idle tracking proxy polling interval pass status working loop thread pass server alive rate struct.
                } else {
                    // Update proxy batch interval tick pass information percentual bar pointer mount alloc UI feedback e task loop text mount log locale payload information info struct layer base hook mount point cycle.
                    setState(prevState => ({
                        ...prevState,
                        dubbingProgress: statusResponse.progress,
                        dubbingStage: statusResponse.stage
                    }));
                }
                
                // Sleep allocator delay asincrono proxy locale limit loop. Sospende esecuzione 3000ms rilasciando control stack UI local event loop. Impedisce saturamento polling API proxy network traffic DOS limit request host backend.
                await new Promise((resolve) => setTimeout(resolve, 3000));
           } 
        } catch (error) {
            // Ultimate trap exception filter limit array. Propaga ed incapsula string target fallback route tree mount exception obj array string pointer limit proxy pass handle locale UI banner alloc proxy payload handler stack throw exception base.
            // Usiamo prevState in callback mutation proxy locale safety object array map per merge drop exception target struct limit.
            setState(prevState => ({
                ...prevState,
                currentStep: 'ERROR',
                // Extraction TypeGuard pattern checking pointer limit instance struct payload message proxy alloc fail log exception catch root limit fall fallback log error array string proxy mount log locale route tree alloc hook pass data object error interface.
                error: error instanceof Error ? error.message : "Fallimento critico nell'orchestratore del Worker video."
            }));
        }
    }

    // Export boundary limit array. Rendiamo fruibile struct logica base hook proxy pass actions setter data export per struct array map access consumer logic root mount JSX object pointer target limit scope UI React hook pass data root proxy export wrapper tree.
    return {
        // State master reader readonly root limit data reference node array limit binding proxy mount access array object struct reference
        state,
        // Handlers wrapper proxy alloc action dispatchers loc async await logic pass data structure export node hook pass boundary limit struct method list export proxy tree map object export alloc loop logic wrapper hook boundary node function handlers return pointer loop root list node
        setFile,
        startTranscription,
        startTranslation,
        startDubbing
    };
}