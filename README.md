# 🎬 Vovio - Automated Video Dubbing Pipeline

![Next.js](https://img.shields.io/badge/Next.js%2016-black?style=for-the-badge&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React%2019-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)
![Python](https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS_v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

**Vovio** è una piattaforma avanzata e altamente ottimizzata per la trascrizione, traduzione e doppiaggio automatizzato di contenuti video. 

Progettata con una moderna architettura a microservizi disaccoppiata, Vovio sfrutta un ecosistema di **Agenti AI specializzati** per estrarre il parlato, adattare i copioni garantendo l'isocronia (sincronismo labiale/temporale) e sintetizzare l'audio clonando la voce originale.

---

## 🏗️ Architettura del Sistema

Il progetto adotta un solido pattern **Orchestratore-Worker**, separando in modo netto l'interfaccia utente, la gestione delle API e i complessi calcoli dei modelli AI.

- 🖥️ **Frontend (Next.js 16 & React 19):** Interfaccia utente fluida stilizzata con Tailwind CSS v4. Implementa una macchina a stati per tracciare il processo e utilizza un sistema di **short-polling asincrono** (ogni 3 secondi) per aggiornare l'avanzamento del doppiaggio senza saturare il sistema.
- ⚙️ **Backend Orchestrator (FastAPI):** Funge da router puro. Gestisce l'upload dei flussi video in directory temporanee e delega il calcolo pesante agli agenti AI tramite `BackgroundTasks` non bloccanti.

### 🧠 L'Ecosistema degli Agenti AI

L'intelligenza artificiale di Vovio è suddivisa in tre moduli isolati e specializzati:

1. 🎙️ **TranscriptionAgent (`faster-whisper`):** Esegue la trascrizione audio estraendo segmenti precisi e annotando i timestamp. Ottimizzato per l'efficienza con quantizzazione `int8` su CPU e una `beam_size` di 5.
2. 🧠 **TranslationAgent (`Agno` + `gemini-2.5-flash`):** Il cuore dell'adattamento. Agisce come un vero "Adattatore Cinematografico" tramite rigorosi *Constraint Prompt*. Garantisce l'**isocronia** costringendo il testo tradotto a mantenere una lunghezza sillabica paragonabile all'originale (+/- 10%), preservando l'ordine topologico delle frasi.
3. 🗣️ **SynthesizerAgent (`Coqui-TTS xtts_v2`):** Gestisce il Text-to-Speech e la clonazione vocale. Per evitare il problema del collasso dell'attenzione (attention collapse), esegue un *chunking intelligente* del testo basato sulla punteggiatura prima di generare e concatenare l'audio.

---

## 📋 Prerequisiti

Prima di iniziare, assicurati di avere installato:
- **Node.js** (v18 o superiore) e `npm`
- **Python** (v3.10 o superiore)
- **FFmpeg** installato e correttamente configurato nel PATH di sistema.

---

## 🛠️ Configurazione dell'Ambiente (.env)

Il progetto richiede la configurazione di due file `.env` per gestire l'hardware e le chiavi API.

### 1. Configurazione Hardware (Root)
Nella cartella principale del progetto (root), crea un file `.env`:
```bash
cp .env.example .env
```
Apri il file e imposta la variabile hardware in base al tuo sistema:

- USE_CUDA=1 👉 Se hai una GPU Nvidia e vuoi scaricare i binari PyTorch per CUDA (accelerazione hardware).

- USE_CUDA=0 (o lascia vuoto) 👉 Per l'installazione standard basata su CPU (fallback automatico).

### 2. Configurazione Backend (Chiavi API)
Spostati nella cartella del backend (apps/backend/) e crea il file .env:
```bash
cd apps/backend
cp .env.example .env
```
Apri il file e configura i seguenti parametri essenziali:
```bash
# Obbligatorio per abilitare l'uso dei modelli TTS di Coqui AI
COQUI_TOS_AGREED=1

# Inserisci la tua chiave API per l'agente di traduzione
GROQ_API_KEY=la_tua_chiave_api_qui
```
## 🚀 Avvio dell'Ambiente di Sviluppo

Vovio è dotato di un setup DevX automatizzato. Gli script di avvio si occupano di creare ambienti virtuali isolati, scaricare la build corretta di PyTorch (CPU o GPU), sincronizzare pacchetti pip e npm in modo idempotente e lanciare i server in parallelo.

Torna nella cartella principale (root) ed esegui il comando corrispondente al tuo sistema operativo:

Windows:
```dos
.\start_dev.bat
```
Linux / macOS:
```dos
chmod +x start_dev.sh
./start_dev.sh
```
Cosa succede ora? > Il Backend (FastAPI) si avvierà in background sulla porta 8000, mentre il Frontend (Next.js) partirà in foreground nel tuo terminale.

## 🛑 Spegnimento

Per terminare l'applicazione in modo pulito ed evitare processi "zombie" in background:

- Premi ripetutamente CTRL+C nel terminale dove è in esecuzione lo script.

- Lo script intercetterà il segnale e invierà una richiesta di chiusura coordinata a tutti i microservizi, liberando le porte TCP.
