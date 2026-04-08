from agno.agent import Agent
from agno.models.groq import Groq
from pydantic import BaseModel, Field
import json

# Pattern Architetturale: Data Transfer Object (DTO) via Pydantic.
# Sfruttiamo i modelli formali per vincolare l'output dell'LLM a uno schema JSON deterministico.
class TranslatedLine(BaseModel):
    id: int = Field(description="L'ID numerico originale della riga (es. 0, 1, 2)")
    # Pattern "Chain of Thought" (CoT) forzato a livello di schema:
    # Richiedendo le note prima del testo, obblighiamo l'engine LLM a compiere un'analisi 
    # di congruenza sillabica e metrica, aumentando l'accuratezza del lip-sync finale.
    adaptation_notes: str = Field(description="Analisi tecnica dell'adattatore: stima delle sillabe (originale vs target), allineamento delle labiali (B, P, M) e vocali aperte, e motivazione delle scelte di adattamento non letterale.")
    text: str = Field(description="La battuta finale adattata. Deve suonare naturale, parlata e perfetta per il lip-sync.")

class DubbingScript(BaseModel):
    # Struttura contenitore (Root Node) per l'array di segmenti elaborati.
    lines: list[TranslatedLine] = Field(description="Lista di tutte le battute adattate")

class TranslationAgent:
    """
    Agente LLM specializzato nell'adattamento cine-televisivo.
    Implementa logiche di Prompt Engineering avanzate (isocronia, restrizioni fonetiche)
    e garantisce un output tipizzato avvalendosi del supporto nativo per JSON Schema di Groq.
    """
    def __init__(self, target_language: str = "eng", model_id: str = "llama-3.3-70b-versatile"):
        # Normalizzazione del target linguistico per stabilizzare la deterministica del prompt.
        language_map = {
            "en": "Inglese",
            "es": "Spagnolo",
            "fr": "Francese",
            "de": "Tedesco",
            "eng": "Inglese"
        }
        
        self.target_language = language_map.get(target_language.lower(), target_language)
        
        # Inizializzazione del core Agent tramite Agno.
        # Definendo 'output_schema', previeniamo le allucinazioni testuali imponendo un parsing JSON rigoroso.
        self.agent = Agent(
            model=Groq(id=model_id),
            output_schema=DubbingScript,
            description="Sei il Direttore del Doppiaggio e Adattatore Cinematografico Senior. Il tuo lavoro NON è fare traduzioni letterali, ma creare ADATTAMENTI PER IL DOPPIAGGIO (Lip-Sync).",
            instructions=[
                # Ancoraggio esplicito e contestuale della lingua sorgente ('Italiano') per isolare le derive morfologiche interne.
                f"OBIETTIVO: Adattare il copione originale DALL'ITALIANO in {self.target_language} per un doppiaggio con sincronia labiale (lip-sync) perfetta.",
                "REGOLE D'ORO DELL'ADATTAMENTO:",
                "1. ISOCRONIA SILLABICA: Non contare le parole, conta le SILLABE. Il testo di destinazione deve avere un tempo di pronuncia identico all'originale.",
                "2. RINUNCIA ALLA LETTERALITÀ: Se una traduzione esatta è troppo lunga o troppo corta, stravolgi la frase. Usa sinonimi, idiomi, ometti dettagli o aggiungi riempitivi pur di mantenere la lunghezza.",
                "3. SINCRONIA LABIALE (FONETICA): Fai attenzione agli attacchi e alle chiusure. Cerca di far coincidere le consonanti bilabiali (B, P, M) nei punti in cui la bocca si chiude nel video.",
                "4. FLUIDITÀ PARLATA: Le frasi devono suonare come se fossero dette da una persona reale, non lette da un libro. Evita costruzioni grammaticali rigide.",
                "Compila sempre il campo 'adaptation_notes' per dimostrare che hai bilanciato sillabe e labiali prima di scrivere il 'text' finale."
            ]
        )
    
    def translate(self, chunks: list[dict]):
        """
        Gestore dell'inferenza in batch per array di sottotitoli. 
        Mantiene rigorosamente l'integrità topologica (ordine temporale) degli stream, analizzando anche chunk vuoti.
        """
        try:
            payload_lines = []
            empty_indices = set()  # Indici intrinsecamente vuoti salvati in Heap pre-computazionale O(1)

            # Pre-processing topologico: inietta identificatori per il mapping post-inferenza.
            for i, chunk in enumerate(chunks):
                original_text = chunk.get("text", "").strip()
                if original_text:
                    payload_lines.append(f"[{i}] {original_text}")
                else:
                    # Caching logico dei chunk silenti: evita il processing superfluo 
                    # prevendendo altresì un falso fallback retroattivo in lingua originale.
                    empty_indices.add(i)  
            
            enriched_payload = "\n".join(payload_lines)
            
            # Costruzione dinamica del prompt pre-inferenza. Passato al target di esecuzione per 
            # forzare la priorità dei task d'azione sull'engine.
            prompt = (
                f"Adatta le seguenti battute dall'Italiano al {self.target_language} "
                f"per il doppiaggio con lip-sync. "
                f"Restituisci TUTTE le righe nel formato richiesto.\n\n"
                f"{enriched_payload}"
            )
            response = self.agent.run(prompt)
            script_data = response.content

            # Type Guard a runtime: Se il wrapper LLM emittente ritorna nativamente una stringa cruda in luogo 
            # dell'atteso DTO in JSON, quest'ultima viene re-idratata forzatamente nell'istanza Pydantic.
            if isinstance(script_data, str):
                script_data = DubbingScript(**json.loads(script_data))

            # Telemetria passiva per monitoraggio dell'ecosistema CoT su Stdout locale
            for line in script_data.lines:
                print(f"ID [{line.id}] Analisi: {line.adaptation_notes}\n-> {line.text}\n")
            
            # Strutturazione Hash Table per lookup rapido a O(1). Costruito per marginare i rischi 
            # di desincronizzazione causata da probabili frame-loss dell'LLM (chiavi perse a run-time).
            translation_map = {line.id: line.text for line in script_data.lines}
            
            final_translations = []
            
            # Ricostruzione Vettoriale: Garantisce la rigidità morfologica dell'array resituito:
            # pari grandezza e indici coincidenti con `len(chunks)`.
            for i in range(len(chunks)):
                if i in empty_indices:
                    # Inserimento "noop" sicuro per flussi nulli, arginando il fallimento sul recupero dizionario.
                    final_translations.append("")
                else:
                    # Strategia di Fallback (Graceful Degradation): in rari casi di "keymiss" dovuti ad un 
                    # drop dell'LLM preserviamo lo slot temporale per non scomporre le label a seguire (Lip-Sync shift).
                    translated_text = translation_map.get(i, chunks[i].get("text", ""))
                    final_translations.append(translated_text)
                
            return final_translations

        except Exception as e:
            # Wrapping try-catch per facilitare l'event-bubbling su microservizio parent (FastAPI, ecc).
            return f"[ERRORE DI TRADUZIONE]: {str(e)}"