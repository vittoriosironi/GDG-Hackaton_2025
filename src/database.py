import chromadb
# from chromadb.config import Settings # Settings è deprecato per l'inizializzazione del client
import google.generativeai as genai
import os

try:
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente. "
                         "Per favore, imposta la variabile d'ambiente GEMINI_API_KEY.")
    genai.configure(api_key=API_KEY)
    print("API Key Gemini configurata con successo.")
except ValueError as e:
    print(f"Errore: {e}")
    # exit()
except Exception as e:
    print(f"Errore imprevisto durante la configurazione della API key di Gemini: {e}")
    # exit()

EMBEDDING_MODEL_NAME = "models/embedding-001"

try:
    client = chromadb.PersistentClient(path="./my_chroma_db")
except Exception as e:
    print(f"Errore durante l'inizializzazione di ChromaDB PersistentClient: {e}")
    # exit()


collection_name = "sessions_summaries_rag" # Potresti voler usare un nome diverso per la collezione RAG
try:
    collection = client.get_collection(name=collection_name)
    print(f"Caricata collezione esistente: {collection_name}")
except Exception:
    print(f"Collezione '{collection_name}' non trovata o errore nel caricarla. Creazione in corso...")
    try:
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Creata nuova collezione: {collection_name}")
    except Exception as e:
        print(f"Errore durante la creazione della collezione ChromaDB '{collection_name}': {e}")
        # exit()


def add_summaries_to_db(summaries_data):
    if not summaries_data:
        print("Nessun riassunto da aggiungere.")
        return
    if not collection:
        print("Errore: la collezione ChromaDB non è inizializzata.")
        return

    ids = [str(data["id"]) for data in summaries_data]
    documents = [data["summary_text"] for data in summaries_data]
    
    metadatas = [data.get("metadata", {}) for data in summaries_data]

    print(f"Generazione embeddings per {len(documents)} documenti con il modello {EMBEDDING_MODEL_NAME}...")
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=documents,
            task_type="RETRIEVAL_DOCUMENT"
        )
        embeddings = result['embedding']
        print(f"Embeddings generati. Numero di vettori: {len(embeddings)}")

        collection.add(
            embeddings=embeddings,
            documents=documents,
            ids=ids,
            metadatas= {
                "timestamp_sessione": "2025-05-11T10:00:00Z",
                "id_sessione_originale": "session_log_001",
                "tipo_attivita_principale": "programmazione",
                "punteggio_produttivita": 0.6
            } # Aggiungi i metadati qui
        )
        print(f"Aggiunti {len(documents)} riassunti (con metadati) al database.")
    except Exception as e:
        print(f"Errore durante la generazione degli embeddings o l'aggiunta al DB: {e}")


def search_summaries(query_text, n_results=3, filter_metadata=None):
    if not query_text:
        print("La query non può essere vuota.")
        return None
    if not collection:
        print("Errore: la collezione ChromaDB non è inizializzata.")
        return None

    print(f"Generazione embedding per la query con il modello {EMBEDDING_MODEL_NAME}...")
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=query_text,
            task_type="RETRIEVAL_QUERY"
        )
        query_embedding = [result['embedding']]

        print("Embedding della query generato. Esecuzione della ricerca...")

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=filter_metadata,
            include=['documents', 'distances', 'metadatas']
        )
        return results
    except Exception as e:
        print(f"Errore durante la ricerca dei riassunti: {e}")
        return None


if __name__ == "__main__":
    if 'collection' not in globals() or not collection:
        print("Impossibile procedere: la collezione ChromaDB non è stata inizializzata correttamente.")
    else:
        # Dati di esempio con metadati per RAG
        example_summaries_rag = [
            {
                "id": "rag_summary_1",
                "summary_text": "L'utente ha mostrato alta concentrazione lavorando su task di programmazione per 2 ore nella sessione mattutina.",
                "metadata": {
                    "timestamp_sessione": "2025-05-11T10:00:00Z",
                    "id_sessione_originale": "session_log_001",
                    "tipo_attivita_principale": "programmazione",
                    "punteggio_produttivita": 0.6
                }
            },
            {
                "id": "rag_summary_2",
                "summary_text": "Produttività media nel pomeriggio, con alcune interruzioni dovute a social media durante la scrittura di email.",
                "metadata": {
                    "timestamp_sessione": "2025-05-11T15:30:00Z",
                    "id_sessione_originale": "session_log_002",
                    "tipo_attivita_principale": "email",
                    "punteggio_produttivita": 0.5
                }
            },
            {
                "id": "rag_summary_3",
                "summary_text": "L'utente ha completato con successo il report finanziario in anticipo rispetto alla scadenza.",
                "metadata": {
                    "timestamp_sessione": "2025-05-10T16:00:00Z",
                    "id_sessione_originale": "session_log_003",
                    "tipo_attivita_principale": "reporting",
                    "punteggio_produttivita": 0.9
                }
            },
            {
                "id": "rag_summary_4",
                "summary_text": "Bassa produttività registrata oggi, molte pause e poca attività significativa sui task di programmazione assegnati.",
                "metadata": {
                    "timestamp_sessione": "2025-05-11T11:00:00Z",
                    "id_sessione_originale": "session_log_004",
                    "tipo_attivita_principale": "programmazione",
                    "punteggio_produttivita": 0.3
                }
            },
            {
                "id": "rag_summary_5",
                "summary_text": "Sessione di brainstorming molto produttiva con il team marketing, generate nuove idee per la campagna del Q3.",
                "metadata": {
                    "timestamp_sessione": "2025-05-09T14:00:00Z",
                    "id_sessione_originale": "session_log_005",
                    "tipo_attivita_principale": "meeting",
                    "punteggio_produttivita": 0.4
                }
            }
        ]

        add_summaries_to_db(example_summaries_rag)

        try:
            print(f"\nNumero totale di elementi nella collezione: {collection.count()}")
        except Exception as e:
            print(f"Errore nel contare gli elementi della collezione: {e}")


        search_query_rag = "Quali attività di programmazione sono state svolte e come è andata la concentrazione?"
        print(f"\nRicerca RAG per: '{search_query_rag}'")
        search_results_rag = search_summaries(search_query_rag, n_results=2)


        if search_results_rag and search_results_rag['documents'] and search_results_rag['documents'][0]:
            print("Risultati della ricerca (per RAG):")
            for i, doc_text in enumerate(search_results_rag['documents'][0]):
                distance = search_results_rag['distances'][0][i]
                retrieved_metadata = search_results_rag['metadatas'][0][i] if search_results_rag['metadatas'] else {}
                print(f"  --- Documento {i+1} ---")
                print(f"  Testo: {doc_text}")
                print(f"  Distanza: {distance:.4f}")
                print(f"  Metadati: {retrieved_metadata}")
                # In un vero RAG, questo testo e/o i metadati verrebbero usati per costruire il prompt per l'LLM
        else:
            print("Nessun risultato trovato o errore nella ricerca.")