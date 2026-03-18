#Importazione della classe Path per la manipolazione dei percorsi del file system
from pathlib import Path

#Definizione della directoru radice del backend calcolata dinamicamente per garantire la portabilità
BASE_DIR = Path(__file__).resolve().parent

#Creazione del percorso temporaneo per il processamento dei flussi multimediali
TEMP_DIR = BASE_DIR / "temp"

#Validazione ed eventuale creazione della directory temporanea
TEMP_DIR.mkdir(parents=True, exist_ok=True)

