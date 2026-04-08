from agno.agent import Agent

from agno.models.google import Gemini

import re

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
    
    def translate(self, chunks: list[dict]):
        """
        Riceve l'intero array di segmenti audio estratti dal trascriber upstream.
        Il metodo è predisposto per la serializzazione topologica, mappando ogni chunk 
        a un indice univoco. Questo garantisce la Context Window globale all'LLM 
        forzando il mantenimento dell'isocronia tramite Constraint Prompting.

        Args:
            chunks (list[dict]): Lista di dizionari contenente il payload acustico estratto.

        Returns:
            str: Il copione globale tradotto e numerato per l'orchestrazione TTS.

        """
        try:
            # Compone un payload indicizzato riga per riga. 
            # Inietta esplicitamente un ID per mappare l'output alle frasi tradotte ai rispettivi timestamp originali.
            payload_lines = []
            for i, chunk in enumerate(chunks):
                original_text = chunk.get("text", "").strip()
                if original_text:
                    payload_lines.append(f"[{i}] {original_text}")
            
            # Serializza la struttura da array a stringa per l'injection nel batch prompt
            enriched_payload = "\n".join(payload_lines)
            
            # Esecuzione asincrona/sincrona della chiamata all'LLM (agente)
            response = self.agent.run(enriched_payload)
            raw_output = response.content
            print(f"--- RAW LLM OUTPUT ---\n{raw_output}\n----------------------")
            
            # Estrazione sicura tramite Regex: estrapola il pattern [ID] Testo.
            # Serve a mitigare potenziali allucinazioni in cui l'LLM aggiunge testo spurio (verbosity pre/post generazione)
            pattern = r"(?:\[)?(\d+)(?:\]|\.|:)?\s*(.*)"
            matches = re.findall(pattern, raw_output)

            # Costruisce una mappa hash per un rapido lookup in O(1) in fase di ricostruzione vettoriale
            translation_map = {int(idx): text.strip() for idx, text in matches}
            
            final_translations = []
            # Scorre l'array originale garantendo il mantenimento dell'ordinamento topologico dei frammenti (chunk)
            for i in range(len(chunks)):
                # Strategia di Fallback (Graceful Degradation): se il modello perde un indice, 
                # preferiamo iniettare la stringa grezza originale piuttosto che dereferenziare un indice mancante
                # causando sfasamenti in downstream (sync audio/video scorretto)
                translated_text = translation_map.get(i, chunks[i].get("text", ""))
                final_translations.append(translated_text)
                
            return final_translations

        except Exception as e:
            # Gestione base degli errori: restituisce una stringa formattata con il dettaglio dell'eccezione
            return f"[ERRORE DI TRADUZIONE]: {str(e)}"
        
        
        
