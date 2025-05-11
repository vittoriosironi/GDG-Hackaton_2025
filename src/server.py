from flask import Flask, request, jsonify, abort
from activity_tracker import SessionTracker 

app = Flask(__name__)

# Stato della sessione (solo uno)
session_active = False

@app.post("/start-session")
def start_session():
    global session_active
    if session_active:
        return jsonify({"error": "Sessione già attiva"}), 400
    session_active = True
    SessionTracker.start_session()
    return jsonify({"status": "started"})

@app.post("/stop-session")
def stop_session():
    global session_active
    if not session_active:
        return jsonify({"error": "Nessuna sessione attiva"}), 400
    session_active = False
    SessionTracker.stop_session()
    return jsonify({"status": "stopped"})

@app.post("/message")
def receive_message():
    global session_active
    if not session_active:
        return jsonify({"error": "Sessione non attiva"}), 403
    
    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Contenuto mancante"}), 400
    
    print(f"Messaggio ricevuto: {data['content']}")
    return jsonify({"status": "received"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
