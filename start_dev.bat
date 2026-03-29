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
call venv\Scripts\activate.bat || call .venv\Scripts\activate.bat
REM Lancia Uvicorn. Il comando 'start /B' avvia il processo in background nella stessa finestra.
start /B uvicorn main:app --reload --port 8000
cd ..\..

REM [DevX] Bootstrap del Frontend (Next.js).
echo [Bootstrap] Avvio Frontend (Next.js) in foreground...
cd apps\frontend
REM Lancia il dev server bloccando l'esecuzione dello script.
npm run dev

REM Nota per lo spegnimento: premere CTRL+C piu' volte per terminare il batch. 
REM Se la porta 8000 rimane occupata, chiudere il terminale.