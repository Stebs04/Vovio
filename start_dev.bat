@echo off
REM [DevX] Configurazione Hardware Dinamica (Template Configuration Pattern).
REM Se esiste il file .env locale, lo legge ignorando le righe che iniziano con #
IF EXIST .env (
    echo [Bootstrap] Rilevato file .env locale. Estrazione configurazioni...
    FOR /F "eol=# tokens=*" %%i IN (.env) DO set %%i
)

REM Sensible Default: Se la variabile non e' stata definita nel .env, forza il fallback a 0.
IF NOT DEFINED USE_CUDA set USE_CUDA=0
echo [Bootstrap] Inizializzazione Ambiente Vovio. Modalita' CUDA: %USE_CUDA%

REM [DevX] Bootstrap del Backend (FastAPI).
echo [Bootstrap] Avvio Backend (FastAPI) in background...
cd apps\backend
REM Attiva il Virtual Environment isolato di Windows.
REM [PROVISIONING: Virtual Environment Isolation]
    REM Verifica l'esistenza del venv. Se assente, lo crea ex-novo per isolare le dipendenze.
    IF NOT EXIST venv (
        echo [Bootstrap] Creazione Virtual Environment per il Backend...
        py -3.12 -m venv venv
    )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip setuptools wheel

    REM [PROVISIONING: Environment-Aware Dependency Injection]
    REM Risoluzione dinamica dei binari tensoriali pesanti. Evita l'Hardware Lock-in
    REM scaricando la build ottimizzata per CPU o GPU in base alla configurazione locale.
    IF "%USE_CUDA%"=="1" (
        echo [Bootstrap] Hardware Target: GPU. Installazione PyTorch CUDA...
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ) ELSE (
        echo [Bootstrap] Hardware Target: CPU. Installazione PyTorch CPU...
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    )

    REM [PROVISIONING: Dependency Syncing]
    REM Sincronizza il resto dell'ecosistema. Essendo un processo idempotente, saltera'
    REM istantaneamente i pacchetti gia' presenti (incluso PyTorch appena installato).
    echo [Bootstrap] Sincronizzazione dipendenze da requirements.txt...
    pip install -r requirements.txt
REM Lancia Uvicorn. Il comando 'start /B' avvia il processo in background nella stessa finestra.
start /B uvicorn main:app --reload --port 8000
cd ..\..

REM [DevX] Bootstrap del Frontend (Next.js).
echo [Bootstrap] Avvio Frontend (Next.js) in foreground...
cd apps\frontend

REM [PROVISIONING: Node Modules Reconciliation]
REM Invochiamo il package manager per verificare e allineare le dipendenze locali
REM con il package.json. Come pip, npm install e' idempotente e scarichera' solo il delta.
echo [Bootstrap] Verifica e installazione dipendenze Frontend...
call npm install

REM Lancia il dev server bloccando l'esecuzione dello script.
npm run dev


REM Nota per lo spegnimento: premere CTRL+C piu' volte per terminare il batch. 
REM Se la porta 8000 rimane occupata, chiudere il terminale.