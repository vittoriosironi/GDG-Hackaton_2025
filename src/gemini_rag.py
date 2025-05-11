import gemini
from typing import Optional
from pydantic import BaseModel, Field
from database import search_summaries
import json

class RagOutput(BaseModel):
    action: str = Field(..., description="")
    query: str = Field(..., description="")
    
def rag(user_question: str):
    prompt_template = f"""
        You are an intelligent assistant that can fetch information from an external vector database
        via a Python function `retrieve(query)`. Whenever the user’s question requires specific data,
        facts, or documents not in your internal knowledge, you must output only this JSON:

        {{
        "action": "retrieve",
        "query": "<text to embed and search>"
        }}

        If instead you can answer directly from your internal knowledge, output only:

        {{
        "action": "answer",
        "query": "<your detailed answer>"
        }}

        Rules:
        - Output strictly valid JSON, nothing else.
        - Keep the “query” short (max 20 words) and focused on the user’s information need.
        - If retrieval is needed, do NOT provide an answer—only the JSON with `"action": "retrieve"`.
        - If the question is general or background knowledge, use `"action": "answer"`.

        User question to process:
        {user_question}

        Now, process the user’s question and return the JSON.  
    """
    out = ""

    # Call Gemini API
    try:
        # Assumendo che gemini.query restituisca una stringa JSON o un oggetto parsabile
        raw_response = gemini.query(content=prompt_template, config={
            "response_mime_type": "application/json", # Richiedi JSON
            "response_schema": RagOutput # Fornisci lo schema Pydantic
        })
        
        print(f"\n--- Risposta raw da Gemini (decisione RAG) ---\n{raw_response}\n--------------------------------------------------")

        # La libreria gemini potrebbe già parsare il JSON se response_schema è usato correttamente.
        # Se raw_response è già un dizionario o un oggetto RagOutput, non serve json.loads.
        # Se è una stringa JSON, allora parsa:
        if isinstance(raw_response, str):
            parsed_response_data = json.loads(raw_response)
        elif isinstance(raw_response, dict): # Se è già un dict
             parsed_response_data = raw_response
        else: # Se è già un oggetto Pydantic (o simile)
            parsed_response_data = raw_response # Assumendo che sia già nel formato corretto o convertibile

        # Valida con Pydantic se non è già un'istanza di RagOutput
        if not isinstance(parsed_response_data, RagOutput):
            decision = RagOutput(**parsed_response_data)
        else:
            decision = parsed_response_data


        if decision.action == "retrieve":
            print(f"\nAzione: RITIRARE. Query per il database: '{decision.query}'")
            if decision.query:
                # Chiama la funzione search_summaries dal file database.py
                retrieved_docs = search_summaries(query_text=decision.query, n_results=3) # Puoi aggiustare n_results
                print("\n--- Documenti recuperati dal database ---")
                if retrieved_docs and retrieved_docs.get('documents') and retrieved_docs['documents'][0]:
                    context_for_generation = []
                    for i, doc_text in enumerate(retrieved_docs['documents'][0]):
                        distance = retrieved_docs['distances'][0][i] if retrieved_docs.get('distances') else 'N/A'
                        metadata = retrieved_docs['metadatas'][0][i] if retrieved_docs.get('metadatas') else {}
                        print(f"  Documento {i+1}: {doc_text} (Distanza: {distance})")
                        print(f"  Metadati: {metadata}")
                        context_for_generation.append(doc_text)
                else:
                    print("Nessun documento trovato o errore nel recupero.")

                context_str = "\n\n---\n\n".join(context_for_generation)

                generation_prompt = f"""
                    You are a helpful assistant. Answer the user's question based ONLY on the provided context.
                    If the context does not contain enough information to answer the question, clearly state that.
                    Do not use any external knowledge. Be concise and directly answer the question.

                    Provided Context:
                    ---
                    {context_str}
                    ---

                    User Question: {user_question}

                    Answer:
                """
                generated_answer = gemini.query(content=generation_prompt)
                print(f"\n--- Risposta generata da Gemini (basata sul contesto) ---\n{generated_answer}\n--------------------------------------------------")
                out = generated_answer
            else:
                print("Errore: Azione 'retrieve' ma nessuna query fornita.")

        elif decision.action == "answer":
            print(f"\nAzione: RISPONDERE DIRETTAMENTE.")
            print(f"Risposta da Gemini: {decision.response}")
            out = decision.response
        else:
            print(f"Errore: Azione non riconosciuta '{decision.action}'.")
        
        return out
    
    except json.JSONDecodeError as e:
        print(f"Errore nel decodificare la risposta JSON da Gemini: {e}")
        print(f"Risposta ricevuta che ha causato l'errore: {raw_response}")
    except Exception as e:
        print(f"Errore imprevisto durante l'elaborazione RAG: {e}")
        # Stampa il traceback per un debug più dettagliato
        import traceback
        traceback.print_exc()

def __main__():
    gemini.init() # Assicurati che gemini sia inizializzato
    
    # Esempi di domande
    question1 = "Parlami della produttività nelle sessioni di programmazione di oggi."
    question2 = "Cos'è l'intelligenza artificiale?"

    print("\nElaborazione Domanda 1...")
    result1 = rag(question1)
    print(f"\n--- Risultato finale per Domanda 1 ---\n{result1}\n------------------------------------")
    
    print("\n*************************************\n")
    
    print("\nElaborazione Domanda 2...")
    result2 = rag(question2)
    print(f"\n--- Risultato finale per Domanda 2 ---\n{result2}\n------------------------------------")

if __name__ == "__main__":
    __main__()