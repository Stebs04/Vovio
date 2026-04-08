"use client";
import { useState, useRef } from 'react';
import Image from "next/image";
import { useVovioPipeline } from "@/hooks/useVovioPipeline";

export default function VovioMainPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetLanguage, setTargetLanguage] = useState<string>("en");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { state, startTranscription, startTranslation, startDubbing } = useVovioPipeline();

  const downloadTextFile = (text: string, filename: string) => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };
    
  const formatSrtTime = (seconds: number | null): string => {
    if (seconds === null || seconds === undefined || isNaN(seconds)) return "00:00:00,000";
    
    const date = new Date(seconds * 1000);
    const hh = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const mm = String(date.getUTCMinutes()).padStart(2, '0');
    const ss = String(date.getUTCSeconds()).padStart(2, '0');
    const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
    return `${hh}:${mm}:${ss},${ms}`;
  };

  // Converte l'array JSON di Whisper in una stringa .srt formattata
  const jsonToSrt = (data: any): string => {
    if (!data) return "";
    
    // Se per qualche motivo è una stringa piana, fai un fallback base
    if (typeof data === "string") {
      return `1\n00:00:00,000 --> 00:00:05,000\n${data}\n`;
    }

    if (Array.isArray(data)) {
      let srtOutput = "";
      
      data.forEach((chunk, index) => {
        let startStr = "00:00:00,000";
        let endStr = "00:00:05,000";

        // Mappatura per il formato di output di default di Whisper (timestamp come array/tupla)
        if (Array.isArray(chunk.timestamp) && chunk.timestamp.length === 2) {
          startStr = formatSrtTime(chunk.timestamp[0]);
          endStr = formatSrtTime(chunk.timestamp[1]);
        } 
        // Fallback per altri formati ASR che usano chiavi start/end dirette
        else if (chunk.start !== undefined && chunk.end !== undefined) {
          startStr = formatSrtTime(chunk.start);
          endStr = formatSrtTime(chunk.end);
        }

        srtOutput += `${index + 1}\n`;
        srtOutput += `${startStr} --> ${endStr}\n`;
        srtOutput += `${chunk.text ? chunk.text.trim() : ""}\n\n`;
      });

      return srtOutput.trim();
    }

    return "";
  };



  return (
    <div className="flex h-screen overflow-hidden bg-[#f7f9fb] text-slate-900">
      {/* SideNavBar - Preso dal design HTML */}
      <aside className="hidden md:flex flex-col h-full w-64 bg-slate-900 p-4 gap-2 z-40 text-white">
       <div className="flex items-center gap-3 px-3 py-6">
  {/* Sostituzione della "V" con l'immagine reale */}
      <div className="w-10 h-10 relative">
        <Image 
          src="/logo.png" 
          alt="Vovio Logo" 
          fill 
          sizes="40px"
          className="rounded-xl object-contain"
          priority 
        />
      </div>
  <div>
    <h2 className="text-xl font-black tracking-tighter text-blue-400">Vovio</h2>
    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">AI Orchestration</p>
  </div>
</div>
        <div className="mt-auto pt-6 border-t border-slate-800">
          <button 
            onClick={() => window.location.reload()}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-xl font-bold text-sm shadow-lg hover:bg-blue-700 transition-all"
          >
            Nuovo Doppiaggio
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto relative">
        <div className="p-8 max-w-7xl mx-auto w-full space-y-8 pb-24">
          
          {/* Header Section */}
          <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Centro di Controllo Vovio</h1>
            </div>
            <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-2xl shadow-sm">
              <span className={`w-2 h-2 rounded-full ${state.currentStep !== 'IDLE' ? 'bg-green-500 animate-pulse' : 'bg-slate-400'}`}></span>
              <span className="text-sm font-semibold text-slate-600">
                Stato: {state.currentStep === 'IDLE' ? 'Inattivo' : 'In elaborazione...'}
              </span>
            </div>
          </section>

          {/* Processing Monitor - Dinamico basato sul progresso reale */}
          {(state.currentStep === 'DUBBING' || state.dubbingProgress > 0) && (
            <section className="bg-white p-8 rounded-2xl shadow-sm border border-blue-100 relative overflow-hidden">
              <div className="flex justify-between items-end mb-6 relative z-10">
                <div className="space-y-1">
                  <p className="text-xs font-bold text-blue-600 uppercase tracking-widest">Pipeline Attiva</p>
                  <h3 className="text-xl font-bold">Fase: {state.dubbingStage?.replace('_', ' ') || 'Sincronizzazione...'}</h3>
                </div>
                <span className="text-2xl font-black text-blue-600">{state.dubbingProgress}%</span>
              </div>
              <div className="h-4 w-full bg-slate-100 rounded-full overflow-hidden relative z-10">
                <div 
                  className="h-full bg-blue-600 rounded-full transition-all duration-500" 
                  style={{ width: `${state.dubbingProgress}%` }}
                ></div>
              </div>
            </section>
          )}

          {/* Upload Section */}
          <section 
            className="group cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className={`bg-white border-2 border-dashed ${selectedFile ? 'border-blue-400 bg-blue-50' : 'border-slate-200'} rounded-2xl p-12 flex flex-col items-center justify-center text-center transition-all hover:border-blue-400`}>
              <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-blue-600">cloud_upload</span>
              </div>
              <h3 className="text-xl font-bold">{selectedFile ? selectedFile.name : 'Carica Video Sorgente'}</h3>
              <p className="text-slate-500 max-w-xs mx-auto mt-2 text-sm">Trascina o clicca per selezionare MP4, MOV o AVI.</p>
              <input 
                type="file" 
                ref={fileInputRef}
                className="hidden" 
                accept="video/*" 
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
            </div>
          </section>

          {/* Control Actions - Collegati alle funzioni dell'hook */}
          <section className="bg-slate-100 p-2 rounded-3xl flex flex-col md:flex-row gap-2">
            <button 
              disabled={!selectedFile || state.currentStep === 'TRANSCRIBING'}
              onClick={() => selectedFile && startTranscription(selectedFile)}
              className="flex-1 bg-white py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-3 hover:bg-slate-50 disabled:opacity-50 transition-all border border-slate-200 shadow-sm"
            >
              <span className="material-symbols-outlined text-blue-600">description</span>
              {state.currentStep === 'TRANSCRIBING' ? 'In corso...' : 'Avvia Trascrizione'}
            </button>
            
            <div className="flex-1 flex gap-2">
              <select 
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
                className="bg-white px-4 rounded-2xl font-bold border border-slate-200 focus:outline-none"
              >
                <option value="en">Inglese</option>
                <option value="es">Spagnolo</option>
                <option value="fr">Francese</option>
              </select>
              <button 
                disabled={!state.transcription}
                onClick={() => startTranslation(targetLanguage)}
                className="flex-1 bg-purple-600 text-white py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-3 hover:opacity-90 disabled:opacity-50 transition-all"
              >
                <span className="material-symbols-outlined">translate</span>
                Traduci
              </button>
            </div>

            <button 
              disabled={!state.translation || !selectedFile}
              onClick={() => selectedFile && startDubbing(targetLanguage, selectedFile.name)}
              className="flex-1 bg-blue-600 text-white py-4 px-6 rounded-2xl font-bold flex items-center justify-center gap-3 hover:opacity-90 disabled:opacity-50 transition-all"
            >
              <span className="material-symbols-outlined">record_voice_over</span>
              Genera Doppiaggio
            </button>
          </section>

          {/* Data Terminals - Visualizzazione JSON dinamica */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Originale */}
            <div className="space-y-4">
              <div className="flex justify-between items-center px-2">
                <h3 className="font-bold flex items-center gap-2">
                  <span className="material-symbols-outlined text-slate-400">code</span>
                  Trascrizione (SRT)
                </h3>
                {state.transcription && (
                  <button 
                    onClick={() => downloadTextFile(jsonToSrt(state.transcription), "trascrizione.srt")}
                    className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">download</span> Scarica .srt
                  </button>
                )}
              </div>
              <div className="bg-slate-900 rounded-2xl p-6 h-64 overflow-y-auto font-mono text-sm text-green-400 shadow-xl">
                {state.transcription ? (
                  <pre>{JSON.stringify(state.transcription, null, 2)}</pre>
                ) : (
                  <p className="text-slate-500 italic">In attesa di trascrizione...</p>
                )}
              </div>
            </div>

            {/* Tradotto */}
            <div className="space-y-4">
              <div className="flex justify-between items-center px-2">
                <h3 className="font-bold flex items-center gap-2">
                  <span className="material-symbols-outlined text-purple-600">language</span>
                  Traduzione (SRT)
                </h3>
                {state.translation && (
                  <button 
                    onClick={() => downloadTextFile(jsonToSrt(state.translation), `traduzione_${targetLanguage}.srt`)}
                    className="text-xs font-bold text-purple-600 hover:underline flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">download</span> Scarica .srt
                  </button>
                )}
              </div>
              <div className="bg-slate-900 rounded-2xl p-6 h-64 overflow-y-auto font-mono text-sm text-purple-300 shadow-xl">
                {state.translation ? (
                  <pre>{JSON.stringify(state.translation, null, 2)}</pre>
                ) : (
                  <p className="text-slate-500 italic">In attesa di traduzione...</p>
                )}
              </div>
            </div>
          </section>

          {/* Final Result Player - Appare solo quando il video è pronto */}
          {state.finalVideoUrl && (
            <section className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start animate-in fade-in slide-in-from-bottom-4 duration-1000">
              <div className="lg:col-span-3 space-y-4">
                <div className="aspect-video bg-black rounded-2xl overflow-hidden relative group shadow-2xl">
                  <video 
                    controls 
                    className="w-full h-full"
                    src={state.finalVideoUrl}
                  />
                </div>
              </div>
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-white p-6 rounded-2xl shadow-sm space-y-6">
                  <h3 className="font-bold text-lg">Pronto per il Download</h3>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 p-3 bg-green-50 rounded-xl">
                      <span className="material-symbols-outlined text-green-600">check_circle</span>
                      <div>
                        <p className="text-sm font-bold">Neural Sync Completato</p>
                        <p className="text-xs text-slate-500">Video generato con successo</p>
                      </div>
                    </div>
                 {/* ... (codice precedente con l'icona check_circle) ... */}
                  </div>
                  
                  {/* Bottone di Download Esistente */}
                  <a 
                    href={state.finalVideoUrl} 
                    download 
                    className="w-full bg-blue-600 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-3 shadow-xl hover:bg-blue-700 transition-all"
                  >
                    <span className="material-symbols-outlined">download</span>
                    Scarica Video Finale
                  </a>
                  
                  {/* INIZIO - NUOVA RIGA DA AGGIUNGERE */}
                  <p className="text-[10px] text-center text-slate-400 font-medium">
                    Dimensione stimata: {selectedFile ? (selectedFile.size / (1024 * 1024)).toFixed(1) : "1.4"} MB • Tempo stimato: ~2m
                  </p>
                  {/* FINE - NUOVA RIGA DA AGGIUNGERE */}

                </div>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}