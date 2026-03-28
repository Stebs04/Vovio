from agno.agent import Agent

from agno.models.google import Gemini

class TranslationAgent:
    """
    Agente responsabile della traduzione del testo.
    Utilizza un modello LLM per convertire il testo nella lingua di destinazione specificata.
    """
    def __init__(self, target_language: str ="eng",  model_id: str="gemini-2.5-flash"):
        """
        Inizializza l'agente di traduzione.

        Args:
            target_language (str): Codice della lingua di destinazione (default: "eng").
            model_id (str): Identificativo del modello OpenAI da utilizzare (default: "gpt-4o-mini").
        """
        # Salva la lingua di destinazione per riferimento futuro
        self.target_language = target_language
        
        # Inizializza l'agente Agno con il modello OpenAI specificato
        # Questo agente gestirà le richieste di traduzione effettive
        # Configurazione dell'agente con istruzioni specifiche per il doppiaggio.
        # Le istruzioni sono rigorose per garantire che l'output sia solo il testo tradotto,
        # pronto per essere passato al modulo TTS (Text-to-Speech) senza metadati indesiderati.
        self.agent = Agent(
            model=Gemini(id=model_id),
            description="Sei un traduttore esperto di doppiaggio cinematografico e contenuti multimediali.",
            instructions=[
                f"Traduci il testo fornito rigorosamente nella lingua: {self.target_language}.",
                "Non aggiungere MAI convenevoli, note, spiegazioni o testo introduttivo.",
                "Preserva il ritmo, le pause e la formattazione originale per facilitare il doppiaggio.",
                "Restituisci ESATTAMENTE E SOLO il testo tradotto."
            ]
        )
    
    def translate(self, text: str):
        """
        Esegue la traduzione del testo fornito.

        Utilizza l'agente configurato per processare il testo in input e restituire
        la versione tradotta nella lingua target.

        Args:
            text (str): Il testo originale da tradurre.

        Returns:
            str: Il testo tradotto, oppure un messaggio di errore formattato se la chiamata fallisce.
        """
        try:
            # Esegue la chiamata all'agente LLM per ottenere la traduzione
            # L'agente utilizzerà le istruzioni di sistema per mantenere il formato corretto
            response = self.agent.run(text)
            
            # Estrae e restituisce il contenuto testuale della risposta
            return response.content
        except Exception as e:
            # Gestione base degli errori: restituisce una stringa formattata con il dettaglio dell'eccezione
            return f"[ERRORE DI TRADUZIONE]: {str(e)}"
        
        
        
