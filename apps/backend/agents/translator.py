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
        
        # Inizializza l'agente Agno con il modello Gemini specificato
        # Questo agente gestirà le richieste di traduzione effettive
        # Configurazione dell'agente con istruzioni specifiche per il doppiaggio.
        # Le istruzioni sono rigorose per garantire che l'output sia solo il testo tradotto,
        # pronto per essere passato al modulo TTS (Text-to-Speech) senza metadati indesiderati.
        self.agent = Agent(
            model=Gemini(id=model_id),
            # [PATTERN: Persona Adoption]
            # Inizializzo il modello forzando l'assunzione di ruolo (Role-Playing).
            description="Sei un Dialoghista e Adattatore Cinematografico Senior. Il tuo unico scopo è adattare copioni per il doppiaggio (Automated Dubbing), garantendo una perfetta isocronia (stessa lunghezza fonologica) rispetto all'audio originale. Devi sacrificare la traduzione letterale a favore della corrispondenza temporale, mantenendo però intatto il significato originario.",
            # [PATTERN: Constraint Prompting & Geometric Bounding]
            # Definizione dei vincoli rigidi (Hard Constraints) per l'output generato.
            # Imponendo un tetto massimo basato sulla geometria del testo originale (character/syllable count),
            # creazione di un Proxy per l'isocronia fonetica. Questo forza il modello a combattere
            # il Text Expansion intrinseco delle traduzioni cross-lingua, garantendo che il downstream
            # TTS operi in un regime di Time-Stretching tollerabile o nullo.
           instructions=[
                f"La lingua di destinazione per il doppiaggio è: {self.target_language}.",
                "VINCOLO DI ISOCRONIA: Ogni singola battuta DEVE avere una lunghezza visiva e un numero di sillabe quasi identico all'originale (+/- 10%).",
                "VINCOLO TOPOLOGICO (CRITICO): Riceverai un copione con righe numerate (es. [0] ..., [1] ...). DEVI restituire la traduzione mantenendo ESATTAMENTE la stessa struttura e la stessa numerazione all'inizio di ogni riga.",
                "Non fondere o unire mai le righe numerate, anche se la fluidità grammaticale lo suggerirebbe. Mantieni la frammentazione acustica originale.",
                "Restituisci ESATTAMENTE E SOLO il copione numerato e tradotto, senza aggiungere note, spiegazioni o convenevoli."
            ]
        )
    
    def translate(self, text: str):
        """
        Esegue la traduzione adattiva del chunk di testo.
        
        Riceve in input non solo il payload semantico (text) ma anche la metrica
        temporale (duration_seconds) derivata dal trascriber upstream. Questo permette
        di calcolare a runtime i vincoli geometrici (Constraint Prompting) necessari
        per garantire l'isocronia ed evitare il time-stretching (effetto chipmunk) nel TTS.

        Args:
            text (str): Il testo originale estratto (es. via Whisper).
            duration_seconds (float): La durata in secondi del chunk audio originale. 
                                      Se 0.0, l'isocronia viene considerata best-effort.

        Returns:
            str: Il testo adattato e isocrono, pronto per il sub-system TTS.
        """
        try:

            # [PATTERN: Dynamic Context Injection]
            # Calcola la geometria della stringa di input a runtime (Proxy Isocronico).
            # Inietta questi metadati in coda al payload testuale, fornendo all'LLM 
            # il target numerico pre-calcolato su cui applicare i vincoli (Hard Constraints)
            # definiti nelle system instructions, abbattendo il rischio di allucinazioni aritmetiche.
            char_count = len(text)
            min_chars = int(char_count * 0.9)
            max_chars = int(char_count * 1.1)
            
            enriched_payload = (
                f"{text}\n\n"
                f"--- METADATI DI CONTROLLO ISOCRONIA ---\n"
                f"Lunghezza originale: {char_count} caratteri.\n"
                f"VINCOLO MATEMATICO: La tua risposta deve essere compresa tra {min_chars} e {max_chars} caratteri totali."
            )

            # Esegue la chiamata all'agente LLM passando il payload arricchito invece del testo grezzo
            response = self.agent.run(enriched_payload)

            # Estrae la stringa utile (payload) dalla risposta dell'agente LLM
            translated_text = response.content
            
            # Calcola le metriche di downstream per validare l'isocronia (Constraint Prompting)
            out_len= len(translated_text)
            delta = out_len - char_count

            # Logging telemetrico a schermo per evidenziare eventuali fallimenti dei vincoli geometrici
            print(f"[TELEMETRIA TRADUTTORE] In: {char_count} chars | Out: {out_len} chars | Delta: {delta} chars")

            return translated_text
        except Exception as e:
            # Gestione base degli errori: restituisce una stringa formattata con il dettaglio dell'eccezione
            return f"[ERRORE DI TRADUZIONE]: {str(e)}"
        
        
        
