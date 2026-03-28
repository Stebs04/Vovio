"use client";
import {useState} from 'react';
import { useVovioPipeline } from "@/hooks/useVovioPipeline";
import Image from 'next/image';

/**
 * @file page.tsx
 * @description Entry point della User Interface (UI) di Vovio.
 * Implementa l'architettura View-Model delegando la logica di business e di stato
 * al custom hook `useVovioPipeline`. Gestisce il layout principale e l'orchestrazione
 * dei flussi di trascrizione, traduzione e sintesi vocale multi-agente.
 * * @module VovioMainPage
 * @requires useVovioPipeline
 */


/**
 * Componente principale della pagina.
 * Inizializza la State Machine tramite `useVovioPipeline` e renderizza
 * il layout a griglia contenente i controlli e i visualizzatori di stato.
 * * @returns {JSX.Element} Il nodo radice dell'interfaccia utente.
 */

export default function VovioMainPage(){

  /**
   * Stato locale per la memorizzazione del file video selezionato dall'utente.
   * Tipizzato rigorosamente come `File | null` per gestire esplicitamente l'assenza di selezione.
   * Questo file verrà passato alla pipeline architetturale al momento dell'avvio.
   */

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  /**
   * Stato locale per la lingua di destinazione del doppiaggio.
   * Inizializzato a 'en' (Inglese) come default. Verrà passato agli agenti di
   * traduzione e sintesi per configurare l'output del modello AI.
   */

  const [targetLanguage, setTargetLanguage] = useState<string>("en");

  const {state, startTranscription, startTranslation, startDubbing} = useVovioPipeline();

  /**
   * Helper function per l'esportazione Client-Side dei testi.
   * Genera un Blob in memoria a partire da una stringa e simula il click
   * su un anchor tag invisibile per attivare il download manager nativo.
   * Ottimizza l'architettura evitando chiamate di rete ridondanti al backend.
   * * @param {string} text - Il contenuto testuale da salvare.
   * @param {string} filename - Il nome del file da proporre all'utente.
   */

  const downloadTextFile= (text: string, filename:string) =>{
    const blob = new Blob([text], {type: "text/plain;charset=utf-8"})
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  return(
    <main className="min-h-screen bg-gray-50 p-8">

      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/** Sezione Header: Titolo e descrizione del cruscotto. Utilizza Flexbox per la spaziatura verticale coerente.*/}
        <header className="flex flex-col gap-2">

          <div className='flex items-center gap-4'>

            <Image src='/logo.png' alt='Vovio Logo Ufficiale' width={48} height={48} priority className='w-12 h-12 object-contain' />

            <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">Vovio Control Center</h1>

          </div>

          <p className="text-gray-500">Pannello di orchestrazione per la pipeline di doppiaggio Multi-Agente</p>

        </header>

        {/* Banner di Feedback Sistema: 
          Visibile solo durante l'elaborazione attiva (Stati diversi da IDLE).
          Sfrutta l'animazione `animate-pulse` per fornire un feedback visivo immediato
          di caricamento asincrono senza appesantire il DOM.
          */}
        {state.currentStep !== 'IDLE' && state.currentStep !== 'ERROR' && (

          <div className='p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 text-sm font-medium animate-pulse'>
            {state.currentStep}
          </div>

        )}

        {state.currentStep === 'ERROR' &&(

          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
            {state.error}
          </div>

        )}

        {/* Card Principale: Contiene i controlli interattivi (Upload, Pulsanti API).
         Implementa un design pulito con padding abbondante e shadow leggera.*/}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-6">
          <h2 className="text-xl font-bold text-gray-800">Caricamento Video e Controlli</h2>

          {/* Selettore File: Limitato nativamente ai formati video tramite l'attributo accept.
          Lo stile del pulsante nativo è sovrascritto tramite i modificatori `file:` di Tailwind. */}
          <input type="file" accept="video/*" className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:font-semibold file:bg-gray-900 file:text-white hover:file:bg-gray-700 cursor-pointer" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}/>
          
          <div className='flex gap-4 mt-2'>
            
            {/* Selettore Lingua: Componente controllato React.
            Il valore è bidirezionalmente legato allo stato `targetLanguage`.*/}
            <div className="flex items-center gap-3 mt-4">

              <label htmlFor='languageSelect' className='text-sm font-medium text-gray-700'>
                Lingua di destinazione:
              </label>

              <select id="languageSelect" value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} className='border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-purple-500 outline-none bg-white'>
                <option value="en">Inglese (EN)</option>

                <option value="es">Spagnolo (ES)</option>

                <option value="fr">Francese (FR)</option>

                <option value="de">Tedesco (DE)</option>

              </select>

            </div>

          </div>

          {/* Pulsantiera di Orchestrazione: 
          I pulsanti sono vincolati alla presenza del file tramite l'attributo disabled 
          e protetti da guard clauses nell'onClick per prevenire chiamate API vuote. */}
          <div className='flex gap-4 mt-2'>

            <button className='px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed' onClick={()=> selectedFile && startTranscription(selectedFile)} disabled={!selectedFile}>
                  Avvia Trascrizione
            </button>

            <button className="px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => startTranslation(targetLanguage)} disabled={!state.transcription}>
              Avvia Traduzione
              </button>

              <button className="px-4 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => {if(selectedFile){startDubbing(targetLanguage, selectedFile.name)}}} disabled={!state.translation || !selectedFile}>
                Genera Doppiaggio
              </button>

          </div>

          
        {/** Fine della prima card */}
        </div>

          {/* * Risultato Trascrizione: 
            * Renderizzato condizionalmente tramite operatore logico AND (&&).
            * Il componente viene montato nel DOM solo quando l'agente Whisper popola lo stato.
          */}

          {state.transcription && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4">

            <h3 className="text-lg font-bold text-gray-800">Trascrizione Originale</h3>

            {/* Contenitore Read-Only: 
            Sfrutta `whitespace-pre-wrap` per preservare le interruzioni di riga (\n) 
            generate nativamente dal modello Whisper, garantendo la leggibilità. 
            */}
            <div className='p-4 bg-gray-50 rounded-xl border border-gray-100'>

              {/*
                * UI State: Rendering the raw API response payload for debugging purposes.
                * Utilizing JSON.stringify to serialize the Object graph into a React-safe String,
                * preventing "Objects are not valid as a React child" invariant violations.
                */}
                <pre className="p-4 bg-gray-900 text-green-400 rounded-md overflow-auto text-xs text-left">

                  <code>{JSON.stringify(state.transcription, null, 2)}</code>

                </pre>

            </div>

            {/* Azione Contestuale: 
                Trigger per l'esportazione Client-Side. 
                Utilizza fallback su stringa vuota (|| "") per conformità rigorosa ai tipi TypeScript.
            */}
            <button onClick={() => downloadTextFile(state.transcription || "","trascrizione.txt")} className='mt-2 self-start px-4 py-2 bg-white border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50 transition-colors'>
                Scarica Trascrizione
              </button>

          </div>)}

          {/* * Risultato Traduzione: 
            * Renderizzato condizionalmente (operatore &&) dipendente dallo stato `translation`.
            * Isolato in una Card dedicata per mantenere la modularità della UI.
          */}
          {state.translation && (

            <div className='bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4'>
              
              <h3 className='text-lg font-bold text-gray-800'>Traduzione Generata</h3>
              {/* Contenitore Read-Only Traduzione: 
                Replica lo stile della trascrizione per coerenza visiva (Design System).
                Inietta la variabile `state.translation` popolata dal TranslationAgent.*/}
              <div className='p-4 bg-gray-50 rounded-xl border border-gray-100'>

               {/*
                  * UI State: Data Inspection for Translation Payload.
                  * Serializing the Translation Agent's output to prevent React rendering crashes,
                  * as the agent maintains the timestamped JSON structure rather than a primitive string.
                  */}
                <pre className="p-4 bg-gray-900 text-green-400 rounded-md overflow-auto text-xs text-left">
                  <code>{JSON.stringify(state.translation, null, 2)}</code>
                </pre>

              </div>
              
              {/* Azione Contestuale Traduzione: 
                Riutilizza la helper function per scaricare il testo tradotto generato
                dal TranslationAgent. Design omogeneo al bottone di trascrizione.
              */}
              <button onClick={() => downloadTextFile(state.translation || "","traduzione.txt")} className='mt-2 self-start px-4 py-2 bg-white border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50 transition-colors'>
                  Scarica Traduzione
              </button>

            </div>

          )} 

          {/* * Risultato Doppiaggio (Player Video): 
            * Renderizzato solo al completamento dell'intera pipeline.
            * Sfrutta il tag nativo HTML5 <video> per il playback con controlli integrati.
            */}
          {state.finalVideoUrl && (

            <div className='bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4'>
              
              <h3 className='text-lg font-bold text-gray-800'>Video Doppiato</h3>

              {/*
              * UI State: Data Inspection for Dubbing Payload (Final Video).
              * Validating the output of the TTS/Dubbing Agent before passing it to the HTML5 video player.
              * Ensures the payload is a valid URL string and not an unexpected nested JSON response.
              */}
              <pre className="p-4 bg-gray-900 text-green-400 rounded-md overflow-auto text-xs text-left mb-4">
                <code>{JSON.stringify(state.finalVideoUrl, null, 2)}</code>
              </pre>

              <video controls={true} className='w-full rounded-xl border border-gray-100 bg-black '
                src={state.finalVideoUrl}
              />

              {/* Azione di Download Video: 
              Sfrutta il tag HTML5 <a> con attributo `download` per invocare il manager di sistema.
              Stilizzato come bottone full-width per massimizzare la Call-To-Action (CTA) finale. 
              */}
              <a href={state.finalVideoUrl} download={true} className='mt-4 flex justify-center items-center w-full py-3 bg-gray-900 text-white font-semibold rounded-xl hover:bg-gray-800 transition-colors'>
                Scarica Video Finale
              </a>

            </div>

          )}

      {/** Fine del div contenitore */}
      </div>

    </main>
  );
}