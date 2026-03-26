"use client";
import {useState} from 'react';
import { useVovioPipeline } from "@/hooks/useVovioPipeline";

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

  return(
    <main className="min-h-screen bg-gray-50 p-8">

      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/** Sezione Header: Titolo e descrizione del cruscotto. Utilizza Flexbox per la spaziatura verticale coerente.*/}
        <header className="flex flex-col gap-2">

          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">Vovio Control Center</h1>

          <p className="text-gray-500">Pannello di orchestrazione per la pipeline di doppiaggio Multi-Agente</p>

        </header>
        {/* Card Principale: Contiene i controlli interattivi (Upload, Pulsanti API).
         Implementa un design pulito con padding abbondante e shadow leggera.*/}

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-6">
          <h2 className="text-xl font-bold text-gray-800">Caricamento Video e Controlli</h2>

          {/* Selettore File: Limitato nativamente ai formati video tramite l'attributo accept.
          Lo stile del pulsante nativo è sovrascritto tramite i modificatori `file:` di Tailwind. */}
          <input type="file" accept="video/*" className="block w-full text-sm 
          text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:font-semibold 
          file:bg-gray-900 file:text-white hover:file:bg-gray-700 cursor-pointer" 
          onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}/>
          
          <div className='flex gap-4 mt-2'>
            
            {/* Selettore Lingua: Componente controllato React.
            Il valore è bidirezionalmente legato allo stato `targetLanguage`.*/}
            <div className="flex items-center gap-3 mt-4">

              <label htmlFor='languageSelect' className='text-sm font-medium text-gray-700'>
                Lingua di destinazione:
              </label>

              <select 
                id="languageSelect"
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
                className='border border-gray-200 rounded-lg px-3 py-1.5 
                text-sm focus:ring-2 focus:ring-purple-500 outline-none bg-white'
              >
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

            <button className='px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg 
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
              onClick={
                ()=> selectedFile && startTranscription(selectedFile)}
                disabled={!selectedFile}>
                  Avvia Trascrizione
            </button>

            <button className="px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 
            disabled:opacity-50 disabled:cursor-not-allowed" 
            onClick={() => startTranslation(targetLanguage)} 
            disabled={!state.transcription}>
              Avvia Traduzione
              </button>

              <button className="px-4 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 
              disabled:opacity-50 disabled:cursor-not-allowed" 
              onClick={() => startDubbing(targetLanguage)} 
              disabled={!state.translation}>
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

              <p className='text-gray-700 whitespace-pre-wrap text-sm leading-relaxed'>
                
                {state.transcription}

                </p> 

            </div>

          </div>)}

            {/* * Risultato Traduzione: 
            * Renderizzato condizionalmente (operatore &&) dipendente dallo stato `translation`.
            * Isolato in una Card dedicata per mantenere la modularità della UI.
            */}

      {/** Fine del div contenitore */}
      </div>

    </main>
  );
}