from TTS.api import TTS
from pathlib import Path
from config import TEMP_DIR
import os

class SynthesizerAgent:
    """
    Agente di sintesi vocale (Text-to-Speech).
    Utilizza un modello avanzato per generare audio parlato a partire da testo,
    supportando clonazione vocale e multilinguismo.
    """
    def __init__(self, model_name: str="tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Inizializza il motore TTS.

        Args:
            model_name (str): Il nome del modello TTS da caricare (default: XTTS v2).
                              XTTS è scelto per le sue capacità di clonazione vocale zero-shot.
        """
        os.environ["COQUI_TOS_AGREED"] = "1"
        #Inizializzazione Motore TTS:
        # Si abilita `agree_to_terms=True` per accettare la licenza CPML in modo programmatico,
        # evitando blocchi interattivi del server. gpu=False garantisce la stabilità su CPU.
        self.tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
    
    def generate_audio(self, text: str, target_language: str, reference_audio_path: str) -> str:
        """
        Genera un file audio a partire dal testo fornito.

        Args:
            text (str): Il testo da sintetizzare.
            target_language (str): Il codice della lingua di destinazione (es. "it", "en").
            reference_audio_path (str): Percorso al file audio di riferimento per la clonazione della voce.

        Returns:
            str: Il percorso assoluto del file audio generato (.wav).
        """
        try:
            # Definisce il percorso di output nella directory temporanea
            output_filename = f"dubbed_{target_language}.wav"
            output_path = str(TEMP_DIR / output_filename)
            
            # Esegue la sintesi vocale
            self.tts.tts_to_file(
                text=text, 
                file_path=output_path, 
                speaker_wav=reference_audio_path, 
                language=target_language
            )
            
            return output_path
        except Exception as e:
            # Gestione errori di sintesi
            return f"[ERRORE TTS]: {str(e)}"