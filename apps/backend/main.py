
# Importa la classe FastAPI dal modulo fastapi
from fastapi import FastAPI

# Inizializza l'applicazione FastAPI
app = FastAPI()

# Definisce un endpoint GET alla radice '/' per verificare lo stato dell'applicazione
@app.get('/')
async def get_status():
    # Restituisce un dizionario con lo stato, il nome dell'app e la versione
    return {
        "status": "operational",
        "app": "vovio",
        "version": "0.1.0"
    }