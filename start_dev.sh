#!/bin/bash

# [DevX] Configurazione Hardware Dinamica (Template Configuration Pattern).
# 1. Verifica l'esistenza del file .env locale (ignorato da Git).
if [ -f ".env" ]; then
    echo "[Bootstrap] Rilevato file .env locale. Estrazione configurazioni..."
    # Estrae solo le variabili valide ignorando i commenti e le inietta nell'ambiente corrente.
    export $(grep -v '^#' .env | xargs)
fi

# 2. Sensible Default (Graceful Degradation).
# Se la variabile USE_CUDA non è stata fornita dal .env, applica il fallback sicuro a 0 (modalità CPU).
export USE_CUDA=${USE_CUDA:-0}
echo "[Bootstrap] Inizializzazione Ambiente Vovio. Modalità CUDA: $USE_CUDA"

# [DevX] Gestione del ciclo di vita dei processi (Anti-Zombie).
# Intercetta il segnale di interruzione manuale (CTRL+C / SIGINT).
# Il comando 'kill 0' propaga il segnale di terminazione a tutti i processi figli, liberando le porte TCP.
trap "echo '[Bootstrap] Spegnimento coordinato dei microservizi...'; kill 0" SIGINT

# [DevX] Bootstrap del Backend (FastAPI).
echo "[Bootstrap] Avvio Backend (FastAPI) in background..."
# Cambio di contesto verso la root del microservizio backend.
cd apps/backend

# [PROVISIONING: Virtual Environment Isolation]
# Verifica l'esistenza del venv. Se assente, lo crea ex-novo per isolare le dipendenze.
if [ ! -d "venv" ]; then
    echo "[Bootstrap] Creazione Virtual Environment per il Backend..."
    python3 -m venv venv
fi

# Attiva il Virtual Environment isolato. Fallback logico (||) tra naming conventions standard.
source venv/bin/activate || source .venv/bin/activate
python3 -m pip install --upgrade pip "setuptools<82" wheel

# [PROVISIONING: Environment-Aware Dependency Injection]
# Risoluzione dinamica dei binari tensoriali pesanti. Evita l'Hardware Lock-in
# scaricando la build ottimizzata per CPU o GPU in base alla configurazione locale.
if [ "$USE_CUDA" = "1" ] || [ "$(echo "$USE_CUDA" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "[Bootstrap] Hardware Target: GPU. Installazione PyTorch CUDA..."
    pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
else
    echo "[Bootstrap] Hardware Target: CPU. Installazione PyTorch CPU..."
    pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
fi

# [PROVISIONING: Dependency Syncing]
# Sincronizza il resto dell'ecosistema. Essendo un processo idempotente, salterà
# istantaneamente i pacchetti già presenti (incluso PyTorch appena installato).
echo "[Bootstrap] Sincronizzazione dipendenze da requirements.txt..."
pip install -r requirements.txt

# Avvia il server ASGI Uvicorn. L'operatore '&' sgancia il processo liberando il main thread dello script.
uvicorn main:app --reload --port 8000 &
# Ritorno strategico alla root del repository (Workspace Root).
cd ../..

# [DevX] Bootstrap del Frontend (Next.js).
echo "[Bootstrap] Avvio Frontend (Next.js) in foreground..."
# Cambio di contesto verso la root del microservizio frontend.
cd apps/frontend

# [PROVISIONING: Node Modules Reconciliation]
# Invochiamo il package manager per verificare e allineare le dipendenze locali
# con il package.json. Come pip, npm install è idempotente e scaricherà solo il delta.
echo "[Bootstrap] Verifica e installazione dipendenze Frontend..."
npm install

# Avvia il dev server Node.js in esecuzione sincrona (bloccante). 
# Manterrà il terminale attivo e stamperà i log fino al segnale di interruzione.
npm run dev