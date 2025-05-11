from flask import Flask, request, jsonify, abort
from activity_tracker import SessionTracker 

app = Flask(__name__)


# Stato della sessione (solo uno)
session_active = False

@app.post("/start-session")
def start_session():
    global session_active
    if session_active:
        return jsonify({"error": "Sessione già attiva"}), 400j
    session_active = True
    global session_tracker
    
    session_tracker = SessionTracker("Study work", ["study mechanics", "see more physics videos"])

    session_tracker.start_tracking()
    return jsonify({"status": "started"})

@app.post("/stop-session")
def stop_session():
    global session_active
    if not session_active:
        return jsonify({"error": "Nessuna sessione attiva"}), 400
    session_active = False
    session_tracker.stop_tracking()
    
    return jsonify({"status": "stopped"})

@app.post("/message")
def receive_message():
    global session_active
    if not session_active:
        return jsonify({"error": "Sessione non attiva"}), 403
    
    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Contenuto mancante"}), 400
    
    content = data['content']
    print(f"Messaggio ricevuto: {content}")
    
    # Risposta generica o logica custom
    risposta = f"Ho ricevuto il tuo messaggio"
    
    return jsonify({
        "status": "received",
        "response": risposta
    })

@app.get("/pull")
def pull_briefs():
    global session_tracker
    global session_active

    if not session_active:
        return jsonify({"error": "Sessione non attiva"}), 403

    if session_tracker is None or not hasattr(session_tracker, "prodanalyzer"):
        return jsonify({"error": "Tracker non inizializzato"}), 500

    briefs = session_tracker.prodanalyzer.briefs
    
    if len(briefs) > 0:
        return jsonify({"brief": briefs[-1]})
    else:
        return jsonify({"brief": ""})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
