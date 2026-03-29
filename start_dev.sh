#!/bin/bash

# [DevX] Configurazione Hardware (Graceful Degradation).
# Iniettiamo la variabile di ambiente nel processo padre. Tutti i worker Python figli la erediteranno.
# Impostare a 1 per forzare l'uso della GPU (se CUDA è correttamente configurato nel sistema).
export USE_CUDA=0
echo "[Bootstrap] Inizializzazione Ambiente Vovio. Modalità CUDA: $USE_CUDA"

# [DevX] Gestione del ciclo di vita dei processi (Anti-Zombie).
# Intercetta il segnale di interruzione manuale (CTRL+C / SIGINT).
# Il comando 'kill 0' propaga il segnale di terminazione a tutti i processi figli, liberando le porte TCP.
trap "echo '[Bootstrap] Spegnimento coordinato dei microservizi...'; kill 0" SIGINT

# [DevX] Bootstrap del Backend (FastAPI).
echo "[Bootstrap] Avvio Backend (FastAPI) in background..."
# Cambio di contesto verso la root del microservizio backend.
cd apps/backend
# Attiva il Virtual Environment isolato. Fallback logico (||) tra naming conventions standard.
source venv/bin/activate || source .venv/bin/activate
# Avvia il server ASGI Uvicorn. L'operatore '&' sgancia il processo liberando il main thread dello script.
uvicorn main:app --reload --port 8000 &
# Ritorno strategico alla root del repository (Workspace Root).
cd ../..

# [DevX] Bootstrap del Frontend (Next.js).
echo "[Bootstrap] Avvio Frontend (Next.js) in foreground..."
# Cambio di contesto verso la root del microservizio frontend.
cd apps/frontend
# Avvia il dev server Node.js in esecuzione sincrona (bloccante). 
# Manterrà il terminale attivo e stamperà i log fino al segnale di interruzione.
npm run dev