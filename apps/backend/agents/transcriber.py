# Importa la classe WhisperModel dalla libreria faster_whisper
from faster_whisper import WhisperModel

# Definisce la classe TranscriptionAgent per gestire la trascrizione audio
class TranscriptionAgent:
    # Metodo di inizializzazione della classe, con dimensione del modello predefinita a "base"
    def __init__(self, model_size: str ="base"):
        # Inizializza il modello WhisperModel specificando la dimensione, il dispositivo (CPU) e il tipo di calcolo (int8)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    # Metodo per trascrivere un file audio dato il suo percorso
    def transcribe(self, audio_path: str):
        # Esegue la trascrizione dell'audio specificato, usando una beam_size di 5
        segments, info= self.model.transcribe(audio_path, beam_size=5)
        # Inizializza una lista vuota per memorizzare i risultati
        result = []
        # Itera su ogni segmento trascritto restituito dal modello
        for segment in segments:
            # Aggiunge un dizionario con tempo di inizio, fine e testo del segmento alla lista dei risultati
            result.append({"start": segment.start, "end": segment.end, "text": segment.text})
        # Restituisce la lista completa dei segmenti trascritti
        return result