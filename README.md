# 🎬 Vovio - Automated Video Dubbing Pipeline

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js%2016-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)](https://pytorch.org/)

**Vovio** è una piattaforma avanzata per la trascrizione, traduzione e doppiaggio automatizzato di contenuti video. Progettata con un'architettura a microservizi disaccoppiata, sfrutta un ecosistema di Agenti AI specializzati per estrarre il parlato, adattare i copioni garantendo l'isocronia e sintetizzare l'audio clonando la voce originale.

---

## 🏗️ Architettura del Sistema

Il progetto adotta un pattern **Orchestratore-Worker**, separando nettamente l'interfaccia utente, la gestione delle API e l'inferenza cruda dei modelli AI.

### 1. Frontend (Next.js & React 19)
Il client è costruito con **Next.js 16.2.1** e **Tailwind CSS v4**. Il cuore logico è racchiuso nell'hook `useVovioPipeline`, una macchina a stati finiti che traccia l'avanzamento (`IDLE`, `TRANSCRIBING`, `TRANSLATING`, `DUBBING`, `SUCCESS`). 
Per le operazioni intensive come il doppiaggio, il client implementa un meccanismo di **short-polling asincrono**, interrogando il backend ogni 3 secondi per aggiornare la UI con la percentuale di completamento senza saturare il Thread Pool.

### 2. Backend Orchestrator (FastAPI)
Il server `main.py` funge da router puro. Riceve il flusso video, persiste i file in una directory temporanea e delega i calcoli agli agenti AI. Utilizza i `BackgroundTasks` di FastAPI per processare il doppiaggio in modo non bloccante, memorizzando lo stato dei job in memoria per rispondere ai poll del client.

### 3. I Componenti AI (The Agents)
L'ecosistema di intelligenza artificiale è suddiviso in tre moduli principali isolati:

* 🎙️ **TranscriptionAgent:** Basato su `faster-whisper`. Esegue la trascrizione su CPU con quantizzazione `int8` per ottimizzare le risorse, dividendo l'audio in segmenti precisi e annotando i timestamp (start/end) con una `beam_size` di 5.
* 🧠 **TranslationAgent:** Costruito sopra il framework `Agno` e interfacciato con il modello `gemini-2.5-flash`. Applica un rigoroso *Constraint Prompting* imponendo al modello il ruolo di "Adattatore Cinematografico". Garantisce l'**isocronia** costringendo il testo tradotto a mantenere una lunghezza sillabica molto simile all'originale (+/- 10%), mantenendo l'ordine topologico delle frasi essenziale per il downstream.
* 🗣️ **SynthesizerAgent:** Utilizza `Coqui-TTS` (`xtts_v2`) per il Text-to-Speech e la clonazione vocale. Per prevenire il collasso dell'attenzione nel modello (attention collapse), l'agente esegue un *chunking* intelligente del testo analizzando la punteggiatura prima di generare l'audio e concatenare i tensori.

---

## 🚀 Guida all'Installazione e Avvio

Il repository è provvisto di un setup "DevX" altamente automatizzato che rileva il tuo sistema operativo ed esegue l'installazione idempotente delle dipendenze.

### Prerequisiti
* **Node.js** (v18+ raccomandata) e `npm`
* **Python 3.10 o superiore**
* **FFmpeg** installato e configurato nel PATH di sistema.

### 1. Configurazione Iniziale
Clona il repository e crea il tuo file di configurazione ambientale nella root directory del progetto:
```bash
cp .env.example .env
```
Nel file .env, imposta la variabile hardware:

+ USE_CUDA=1 se hai una GPU Nvidia e vuoi accelerare l'inferenza AI.

+ USE_CUDA=0 (o lascia vuoto) per il fallback automatico su esecuzione via CPU.

### 2. Avvio dell'Ambiente di Sviluppo
Il progetto include due script gemelli (start_dev.bat per Windows e start_dev.sh per macOS/Linux).

Esegui lo script dalla root del progetto:

**Su Windows:**
```bash
.\start_dev.bat
```
**Su Linux/MacOs:**
```bash
chmod +x start_dev.sh
./start_dev.sh
```
**Cosa fa lo script dietro le quinte?**

1. **Dependency Injection Hardware-Aware:** Crea un virtual environment Python isolato (venv) e, in base al flag USE_CUDA, scarica automaticamente la build corretta di PyTorch (CPU o CUDA 12.1).

2. **Sincronizzazione Dipendenze:** Esegue pip install e npm install in modo idempotente (scarica solo i delta necessari).

3. **Bootstrap Coordinato: Lancia il server uvicorn (Backend)** in background sulla porta 8000 e il frontend server Next.js in foreground.

### 3. Spegnimento
Per terminare l'applicazione in modo pulito e prevendo processi zombie
