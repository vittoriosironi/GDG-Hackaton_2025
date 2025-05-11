import threading
import google.generativeai as genai
import pyautogui
import pytesseract
from PIL import Image
import time
import os
import re
import json
import subprocess

# --- CONFIGURAZIONE ---
GOOGLE_API_KEY = "AIzaSyC8K8ymeN6RTDmGsXVnKUGfEDQBSlMBp0I"
genai.configure(api_key=GOOGLE_API_KEY)
MODEL_NAME = "gemini-2.0-flash"
# MODEL_NAME = "gemini-1.0-pro-latest" # Alternativa

# --------------------------------------------------------------------------- #
# NOTA IMPORTANTE PER UTENTI MACOS:                                           #
# Se lo script non sembra eseguire click o battiture, è MOLTO PROBABILE       #
# che manchino i permessi di Accessibilità.                                   #
# Vai su "Impostazioni di Sistema" > "Privacy e Sicurezza" > "Accessibilità". #
# Assicurati che l'applicazione Terminale (o il tuo IDE, es. VS Code)       #
# abbia il permesso (toggle abilitato).                                       #
# Potrebbe essere necessario sbloccare le impostazioni (lucchetto) e          #
# aggiungere l'app manualmente se non è in lista.                             #
# --------------------------------------------------------------------------- #

# Percorso Tesseract (AGGIORNA SE NECESSARIO)
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract' # Esempio macOS Homebrew
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Esempio Windows

# --- FUNZIONI HELPER ---
'''
def capture_screen_and_extract_elements():
    print("   [DEBUG] Cattura schermo e OCR in corso...")
    screenshot = pyautogui.screenshot()
    # screenshot.save("debug_screenshot.png")
    
    try:
        # Lingue: 'ita+eng' per italiano e inglese. Aggiungi altre se necessario.
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='ita+eng')
    except Exception as e:
        print(f"   [ERRORE OCR] Errore durante OCR con Tesseract: {e}")
        print("   [ERRORE OCR] Assicurati che Tesseract sia installato, nel PATH, e che i file di lingua (es. ita.traineddata) siano presenti.")
        return [], screenshot

    elements = []
    element_id_counter = 0
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if int(data['conf'][i]) > 50 and text and data['level'][i] >= 4 : # livello 4=parola, 3=linea
            (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            if w > 3 and h > 3 and w < screenshot.width * 0.8 and h < screenshot.height * 0.3: # Filtri sensati
                 elements.append({
                    "id": element_id_counter,
                    "text": text,
                    "x": x + w // 2,
                    "y": y + h // 2,
                    "bounds": (x, y, w, h)
                })
                 element_id_counter += 1
    print(f"   [DEBUG] OCR ha trovato {len(elements)} elementi.")
    return elements, screenshot
'''

def capture_screen_and_extract_elements():
    print("   [DEBUG] Cattura schermo e OCR in corso...")
    screenshot = pyautogui.screenshot()
    # screenshot.save("debug_screenshot.png") # Decommenta per debug visivo

    try:
        # Lingue: 'ita+eng' per italiano e inglese.
        # PSM 6: Assume un singolo blocco uniforme di testo. Potrebbe essere migliore per UI.
        # PSM 11: Testo sparso.
        # PSM 3: Default, completamente automatico.
        custom_config = r'--oem 3 --psm 6' # Prova diverse modalità PSM
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='ita+eng', config=custom_config)
    except Exception as e:
        print(f"   [ERRORE OCR] Errore durante OCR con Tesseract: {e}")
        print("   [ERRORE OCR] Assicurati che Tesseract sia installato, nel PATH, e che i file di lingua (es. ita.traineddata) siano presenti.")
        return [], screenshot

    raw_words = []
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        # Livello 5 è 'parola'. Filtra per confidenza e testo non vuoto.
        if int(data['level'][i]) == 5 and int(data['conf'][i]) > 50: 
            text = data['text'][i].strip()
            if text:
                x, y, w, h = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                # Filtri aggiuntivi per dimensioni sensate
                if w > 3 and h > 3 and w < screenshot.width * 0.8 and h < screenshot.height * 0.3:
                    raw_words.append({
                        "text": text,
                        "x": x, "y": y, "w": w, "h": h,
                        "right": x + w, "bottom": y + h,
                        "center_y": y + h // 2
                    })

    if not raw_words:
        print("   [DEBUG] OCR non ha trovato parole grezze.")
        return [], screenshot

    # Ordina le parole per posizione (prima y, poi x) per facilitare il raggruppamento
    raw_words.sort(key=lambda w: (w['center_y'], w['x']))

    grouped_elements = []
    element_id_counter = 0
    
    if not raw_words:
        print(f"   [DEBUG] OCR ha trovato {len(grouped_elements)} elementi raggruppati.")
        return grouped_elements, screenshot

    current_group = [raw_words[0]]
    for i in range(1, len(raw_words)):
        prev_word = current_group[-1]
        current_word = raw_words[i]

        # Criteri per raggruppare:
        # 1. Verticalmente vicini (i centri y non troppo distanti)
        # 2. Orizzontalmente adiacenti (la parola corrente inizia poco dopo la fine della precedente)
        vertical_diff = abs(current_word['center_y'] - prev_word['center_y'])
        horizontal_gap = current_word['x'] - prev_word['right']
        
        # Tolleranze (da aggiustare)
        max_vertical_diff = prev_word['h'] * 0.7 # Max 70% dell'altezza della parola precedente
        max_horizontal_gap = prev_word['w'] * 1.0 # Max 1 volta la larghezza della parola precedente (per spazi)

        if vertical_diff < max_vertical_diff and 0 <= horizontal_gap < max_horizontal_gap:
            current_group.append(current_word)
        else:
            # Finalizza il gruppo precedente
            if current_group:
                group_text = " ".join(w['text'] for w in current_group)
                group_x_min = min(w['x'] for w in current_group)
                group_y_min = min(w['y'] for w in current_group)
                group_x_max = max(w['right'] for w in current_group)
                group_y_max = max(w['bottom'] for w in current_group)
                group_w = group_x_max - group_x_min
                group_h = group_y_max - group_y_min
                
                if group_w > 0 and group_h > 0: # Assicura dimensioni valide
                    grouped_elements.append({
                        "id": element_id_counter,
                        "text": group_text,
                        "x": group_x_min + group_w // 2,
                        "y": group_y_min + group_h // 2,
                        "bounds": (group_x_min, group_y_min, group_w, group_h)
                    })
                    element_id_counter += 1
            current_group = [current_word]

    # Finalizza l'ultimo gruppo
    if current_group:
        group_text = " ".join(w['text'] for w in current_group)
        group_x_min = min(w['x'] for w in current_group)
        group_y_min = min(w['y'] for w in current_group)
        group_x_max = max(w['right'] for w in current_group)
        group_y_max = max(w['bottom'] for w in current_group)
        group_w = group_x_max - group_x_min
        group_h = group_y_max - group_y_min

        if group_w > 0 and group_h > 0:
            grouped_elements.append({
                "id": element_id_counter,
                "text": group_text,
                "x": group_x_min + group_w // 2,
                "y": group_y_min + group_h // 2,
                "bounds": (group_x_min, group_y_min, group_w, group_h)
            })
            element_id_counter += 1
            
    print(f"   [DEBUG] OCR ha trovato {len(grouped_elements)} elementi raggruppati.")
    return grouped_elements, screenshot

def describe_elements_for_llm(elements, max_elements=60): # Aumentato leggermente
    if not elements:
        return "Nessun elemento testuale significativo rilevato sullo schermo."
    
    description = "Elementi testuali rilevati sullo schermo (ID, Testo, Coordinate Approssimative Centro X,Y):\n"
    for el in elements[:max_elements]:
        clean_text = re.sub(r'[^\w\s\.,\-\(\)\[\]\{\}:;\'\"@#\$%\^&\*\+=<>/!\?]', '', el['text']) # Caratteri più permessivi
        if len(clean_text) > 40:
            clean_text = clean_text[:37] + "..."
        if not clean_text.strip():
            continue
        description += f"- ID: {el['id']}, Testo: \"{clean_text}\", Pos: ({el['x']},{el['y']})\n"
    return description

def get_next_action_from_gemini(overall_goal, history, screen_description):
    prompt = f"""Sei un assistente AI esperto e meticoloso che controlla un'interfaccia grafica (GUI) del computer per raggiungere un obiettivo specifico.

Obiettivo generale: "{overall_goal}"
{history if history else "Nessuna azione precedente in questo task."}

Stato attuale dello schermo (elementi testuali rilevati):
{screen_description}

Considerazioni Speciali e Gestione Imprevisti:
- Il tuo compito primario è progredire verso l'obiettivo generale.
- TUTTAVIA, se sullo schermo appaiono elementi inaspettati che sembrano bloccare l'interazione o richiedono un'azione prima di poter continuare (es. pop-up per i cookie, richieste di consenso/notifiche, banner pubblicitari, finestre di dialogo di errore, richieste di login inaspettate), **devi dare priorità alla gestione di questi imprevisti.**
- Per gli imprevisti comuni:
    - **Cookie Pop-up/Banner:** Cerca testi come "Accetta tutti", "Consenti cookie", "OK", "Capito", "Gestisci opzioni", "Rifiuta" o un'icona di chiusura (X). Scegli l'opzione che permette di continuare più rapidamente (spesso "Accetta tutti" o simile).
    - **Richieste di Notifiche/Permessi:** Cerca "Consenti", "Blocca", "Non ora", "Chiudi".
    - **Banner Pubblicitari / Pop-up Promozionali:** Cerca un pulsante "Chiudi", un'icona "X", "Salta", "No grazie".
    - **Errori / Avvisi:** Leggi il messaggio e cerca "OK", "Chiudi", "Annulla".
- **Apertura Applicazioni (macOS):** Quando usi OPEN_APP("NomeApplicazione"), fornisci il nome più completo possibile dell'applicazione (es. "Microsoft Excel" invece di solo "Excel", "Google Chrome" invece di "Chrome"). Se non sei sicuro, puoi usare il nome che appare in Spotlight.
- **Azione suggerita per chiudere pop-up generici:** Spesso `PRESS("esc")` può chiudere finestre di dialogo o pop-up. Consideralo se non vedi un pulsante di chiusura ovvio.
- Dopo aver gestito un imprevisto, rivaluta lo schermo e continua verso l'obiettivo generale.
- Se un elemento sembra cliccabile ma non ha testo (es. un'icona X per chiudere), e le sue coordinate sono chiare dalla descrizione, puoi usare CLICK_XY con cautela.
- Se sei bloccato o non sei sicuro di come gestire un imprevisto o procedere, usa ASK_USER("domanda specifica").

Scegli la *singola* prossima azione per progredire.
Azioni disponibili (USA ESATTAMENTE QUESTO FORMATO):
1.  CLICK_ID(id_elemento) -> Clicca sull'elemento con l'ID. Es: CLICK_ID(10)
2.  CLICK_TEXT("testo_da_cliccare") -> Cerca e clicca testo ESATTO o MOLTO SIMILE. Es: CLICK_TEXT("Accetta tutti i cookie")
3.  CLICK_XY(x, y) -> Clicca coordinate (x,y). USA CON CAUTELA. Es: CLICK_XY(500, 250)
4.  TYPE("testo da scrivere") -> Scrive testo. Es: TYPE("Ciao mondo")
5.  PRESS("nome_tasto") -> Premi tasto speciale (es. "enter", "tab", "esc", "cmd", "ctrl", "alt", "shift", "space", "backspace", "delete", "f5", "cmd+s"). Es: PRESS("esc")
6.  SCROLL("direzione", clicks) -> Scorre. direzione: "up", "down", "left", "right". clicks: numero "scatti" (1-10). Es: SCROLL("down", 5)
7.  WAIT(secondi) -> Attendi (es. 0.5, 1, 2.5). Es: WAIT(1.5)
8.  OPEN_APP("NomeApplicazione") -> Apre un'applicazione. Es: OPEN_APP("Microsoft Excel")
9.  ASK_USER("domanda per l'utente") -> Se bloccato o hai bisogno di info. Es: ASK_USER("Quale file apro?")
10. DONE() -> Se l'obiettivo è completato.

Importante:
- Restituisci *SOLO ED ESCLUSIVAMENTE* l'azione nel formato richiesto. Nessuna altra parola o spiegazione.
- Esempio di output valido: CLICK_TEXT("Accetta tutti i cookie")
- Esempio di output NON valido: Azione: CLICK_ID(12) perché voglio cliccare il pulsante.

Qual è la tua prossima azione?"""

    generation_config = {"temperature": 0.1, "max_output_tokens": 150}
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        print("   [DEBUG] Invio prompt a Gemini...")
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        action_string = response.text.strip()
        print(f"   [DEBUG] Gemini raw response: '{action_string}'")
        
        known_command_patterns = [
            r"CLICK_ID\(\s*\d+\s*\)", r"CLICK_TEXT\(\s*\".*?\"\s*\)", r"CLICK_XY\(\s*\d+\s*,\s*\d+\s*\)",
            r"TYPE\(\s*\".*?\"\s*\)", r"PRESS\(\s*\".*?\"\s*\)", 
            r"SCROLL\(\s*\"(?:up|down|left|right)\"\s*,\s*\d+\s*\)",
            r"WAIT\(\s*\d+\.?\d*\s*\)", r"OPEN_APP\(\s*\".*?\"\s*\)", # <-- AGGIUNTO OPEN_APP
            r"ASK_USER\(\s*\".*?\"\s*\)", r"DONE\(\s*\)"
        ]
        extracted_action = None
        for pattern in known_command_patterns:
            match = re.search(pattern, action_string)
            if match:
                extracted_action = match.group(0).strip() # Prende la prima corrispondenza e la pulisce
                break 
        
        if extracted_action:
            action_string = extracted_action
        elif not action_string:
            print("   [AVVISO] LLM ha restituito una stringa vuota.")
            return "ASK_USER(\"Il modello AI non ha fornito un'azione. Puoi riformulare?\")"
        # Se non estratto ma c'è stringa, la usa così com'è, il parser la valuterà

        print(f"   [LLM Suggerisce (pulito)]: {action_string}")
        return action_string
    except Exception as e:
        print(f"   [ERRORE API Gemini]: {e}")
        if hasattr(e, 'response'): print(f"   [ERRORE API Gemini Dettagli]: {e.response}")
        return "ASK_USER(\"Problema con API LLM. Riprova o riformula.\")"


def find_element_by_id(elements, target_id):
    for el in elements:
        if el['id'] == target_id:
            return el
    return None

def find_element_by_text(elements, target_text, exact_match_threshold=90):
    # Potresti usare `thefuzz` per matching più avanzato: pip install thefuzz python-Levenshtein
    # from thefuzz import fuzz
    best_match_el = None
    highest_similarity = 0
    target_lower = target_text.lower()

    for el in elements:
        el_text_lower = el['text'].lower()
        # Calcolo similarità semplice (Jaccard index per parole o Levenshtein)
        # Per ora, usiamo un "contains" e diamo priorità a match più lunghi/esatti
        if target_lower == el_text_lower: # Match esatto
            return el 
        if target_lower in el_text_lower:
            similarity = len(target_lower) / len(el_text_lower) * 100
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match_el = el
    
    if best_match_el and highest_similarity >= exact_match_threshold / 1.5: # Soglia più permissiva per "contains"
        print(f"   [DEBUG] Trovato testo '{best_match_el['text']}' per '{target_text}' con similarità {highest_similarity:.2f}%")
        return best_match_el
    elif best_match_el: # Se c'è un best_match ma sotto soglia forte, lo segnalo
        print(f"   [DEBUG] Match debole per '{target_text}': '{best_match_el['text']}' ({highest_similarity:.2f}%). Non usato.")
    return None


def execute_action(action_string, current_elements):
    print(f"--- ESECUZIONE AZIONE: {action_string} ---")
    
    # Get screen size for coordinate validation
    screen_width, screen_height = pyautogui.size()
    
    # CLICK_ID(id_elemento)
    match = re.fullmatch(r"CLICK_ID\(\s*(\d+)\s*\)", action_string, re.IGNORECASE)
    if match:
        el_id = int(match.group(1))
        element = find_element_by_id(current_elements, el_id)
        if element:
            # Make sure coordinates are within screen bounds
            x = min(max(0, element['x']), screen_width)
            y = min(max(0, element['y']), screen_height)
            
            print(f"  PYAUTOGUI: CLICK_ID su ID {el_id} ('{element['text']}') @ ({x},{y})")
            time.sleep(0.2) # Piccola pausa prima del click
            
            # Move first, then click separately - more reliable than direct click
            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.1)
            pyautogui.click()
            return True, None
        else:
            msg = f"Elemento con ID {el_id} non trovato."
            print(f"  ERRORE: {msg}")
            return False, msg

    # CLICK_TEXT("testo_da_cliccare")
    match = re.fullmatch(r"CLICK_TEXT\(\s*\"(.*?)\"\s*\)", action_string, re.IGNORECASE)
    if match:
        text_to_click = match.group(1)
        element = find_element_by_text(current_elements, text_to_click)
        if element:
            # Make sure coordinates are within screen bounds
            x = min(max(0, element['x']), screen_width)
            y = min(max(0, element['y']), screen_height)
            
            print(f"  PYAUTOGUI: CLICK_TEXT su \"{text_to_click}\" (trovato '{element['text']}') @ ({x},{y})")
            time.sleep(0.2) # Piccola pausa prima del click
            
            # Move first, then click separately
            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.1)
            pyautogui.click()
            return True, None
        else:
            msg = f"Elemento con testo simile a \"{text_to_click}\" non trovato."
            print(f"  ERRORE: {msg}")
            return False, msg

    # CLICK_XY(x, y)
    match = re.fullmatch(r"CLICK_XY\(\s*(\d+)\s*,\s*(\d+)\s*\)", action_string, re.IGNORECASE)
    if match:
        x, y = int(match.group(1)), int(match.group(2))
        
        # Make sure coordinates are within screen bounds
        x = min(max(0, x), screen_width)
        y = min(max(0, y), screen_height)
        
        print(f"  PYAUTOGUI: CLICK_XY @ ({x},{y})")
        time.sleep(0.2) # Piccola pausa prima del click
        
        # Move first, then click separately
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.1)
        pyautogui.click()
        return True, None
    
    # Rest of the function remains unchanged
    # ...ap

    # TYPE("testo da scrivere")
    match = re.fullmatch(r"TYPE\(\s*\"(.*?)\"\s*\)", action_string, re.IGNORECASE)
    if match:
        text_to_type = match.group(1)
        print(f"  PYAUTOGUI: TYPE '{text_to_type}'")
        time.sleep(0.2) # Piccola pausa prima di scrivere
        pyautogui.typewrite(text_to_type, interval=0.03) # Aumentato leggermente intervallo per stabilità
        return True, None

    # PRESS("nome_tasto")
    match = re.fullmatch(r"PRESS\(\s*\"(.*?)\"\s*\)", action_string, re.IGNORECASE)
    if match:
        key_name = match.group(1).lower().strip()
        keys_to_press = [k.strip() for k in key_name.split('+')]
        print(f"  PYAUTOGUI: PRESS tasti {keys_to_press}")
        time.sleep(0.2) # Piccola pausa prima di premere
        if len(keys_to_press) > 1:
            # Gestione speciale per 'cmd' su macOS se è parte di una hotkey
            processed_keys = ['command' if k == 'cmd' else k for k in keys_to_press]
            pyautogui.hotkey(*processed_keys)
        elif len(keys_to_press) == 1 and keys_to_press[0]:
            key_to_press_single = 'command' if keys_to_press[0] == 'cmd' else keys_to_press[0]
            pyautogui.press(key_to_press_single)
        else:
            print(f"  ERRORE: Nome tasto non valido in PRESS: '{key_name}'")
            return False, f"Nome tasto non valido: {key_name}"
        return True, None

    # OPEN_APP("NomeApplicazione")
    match = re.fullmatch(r"OPEN_APP\(\s*\"(.*?)\"\s*\)", action_string, re.IGNORECASE)
    if match:
        app_name = match.group(1)
        print(f"  AZIONE: OPEN_APP '{app_name}' utilizzando il comando 'open'")
        try:
            # Su macOS, 'open -a "Nome Applicazione"' è il modo più robusto.
            # Assicurati che il nome dell'app sia quello corretto (es. "TextEdit", "Google Chrome")
            subprocess.run(['open', '-a', app_name], check=True)
            print(f"  SUCCESSO: Comando 'open -a \"{app_name}\"' eseguito.")
            time.sleep(2) # Attendi un po' che l'app si apra e diventi attiva
            return True, None
        except FileNotFoundError:
            errmsg = f"Comando 'open' non trovato. Assicurati di essere su un sistema simile a Unix (es. macOS, Linux)."
            print(f"  ERRORE: {errmsg}")
            return False, errmsg
        except subprocess.CalledProcessError as e:
            errmsg = f"Errore durante l'apertura di '{app_name}'. L'app potrebbe non esistere o il nome non è corretto. Dettagli: {e}"
            print(f"  ERRORE: {errmsg}")
            return False, errmsg
        except Exception as e:
            errmsg = f"Errore imprevisto durante OPEN_APP: {e}"
            print(f"  ERRORE: {errmsg}")
            return False, errmsg
    
    # SCROLL("direzione", clicks)
    match = re.fullmatch(r"SCROLL\(\s*\"(up|down|left|right)\"\s*,\s*(\d+)\s*\)", action_string, re.IGNORECASE)
    if match:
        direction = match.group(1)
        clicks = int(match.group(2))
        scroll_val_multiplier = 30 # Pixel per "click" di scroll, aggiustabile
        scroll_amount = clicks * scroll_val_multiplier
        if direction == "up":
            print(f"  PYAUTOGUI: SCROLL UP ({scroll_amount}px)")
            pyautogui.scroll(scroll_amount)
        elif direction == "down":
            print(f"  PYAUTOGUI: SCROLL DOWN ({-scroll_amount}px)")
            pyautogui.scroll(-scroll_amount)
        elif direction == "left": 
            print(f"  PYAUTOGUI: SCROLL LEFT ({-scroll_amount}px orizz.)") # hscroll positivo = destra
            pyautogui.hscroll(-scroll_amount)
        elif direction == "right":
            print(f"  PYAUTOGUI: SCROLL RIGHT ({scroll_amount}px orizz.)")
            pyautogui.hscroll(scroll_amount)
        return True, None

    # WAIT(secondi)
    match = re.fullmatch(r"WAIT\(\s*(\d+\.?\d*)\s*\)", action_string, re.IGNORECASE)
    if match:
        seconds = float(match.group(1))
        print(f"  AZIONE: WAIT per {seconds} secondi")
        time.sleep(seconds)
        return True, None

    # ASK_USER("domanda")
    match = re.fullmatch(r"ASK_USER\(\s*\"(.*?)\"\s*\)", action_string, re.IGNORECASE)
    if match:
        question = match.group(1)
        print(f"  LLM CHIEDE: {question}")
        return False, question 

    # DONE()
    if re.fullmatch(r"DONE\(\s*\)", action_string, re.IGNORECASE):
        print("  LLM SEGNALA: Compito completato.")
        return False, "DONE"

    errmsg = f"Azione '{action_string}' non riconosciuta o formato non valido."
    print(f"  ERRORE: {errmsg}")
    return False, errmsg


# --- MAIN LOOP ---
if __name__ == "__main__":
    print("="*30)
    print(" Assistente GUI Gemini - v0.2 ")
    print("="*30)
    print("Per interrompere PyAutoGUI: muovi rapidamente il mouse nell'angolo in alto a sinistra.")
    print("Premi Ctrl+C nel terminale per uscire dall'assistente.")
    
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1 # Pausa breve dopo ogni azione pyautogui, per stabilità

    overall_goal = input("\nQual è il tuo obiettivo? (es. 'Apri blocco note e scrivi ciao')\n> ")
    
    action_history = []
    max_steps_per_goal = 100

    for step_count in range(max_steps_per_goal):
        print(f"\n--- PASSO {step_count + 1} / {max_steps_per_goal} (Obiettivo: '{overall_goal}') ---")
        
        current_elements, _ = capture_screen_and_extract_elements()
        screen_desc = describe_elements_for_llm(current_elements)
        
        # Debug: mostra descrizione schermo inviata a LLM (può essere molto lunga)
        # if step_count < 2: # Solo per i primi passi
        #     print("\n   [DEBUG] Descrizione Schermo per LLM (parziale):")
        #     print(screen_desc[:500] + "...\n" if len(screen_desc) > 500 else screen_desc)

        action_str = get_next_action_from_gemini(overall_goal, "\n".join(action_history[-5:]), screen_desc)

        if not action_str: # Gestione se get_next_action_from_gemini restituisce None o stringa vuota (improbabile con la logica attuale)
            print("L'LLM non ha restituito un'azione valida. Riprovo al prossimo ciclo.")
            action_history.append("SYSTEM_ERROR: LLM no action returned.")
            time.sleep(2)
            continue

        executed, message_to_user = execute_action(action_str, current_elements)

        if message_to_user == "DONE":
            print(f"\nOBIETTIVO '{overall_goal}' COMPLETATO (secondo l'AI).")
            break
        
        if message_to_user and not executed: # ASK_USER o errore di esecuzione
            if action_str.startswith("ASK_USER"):
                user_response = input(f"AI CHIEDE: {message_to_user}\nLa tua risposta (o 'salta'): ")
                if user_response.lower() == 'salta':
                    action_history.append(f"USER_RESPONSE: Ignorato richiesta AI.")
                else:
                    action_history.append(f"USER_RESPONSE: \"{user_response}\"")
            else: # Errore nell'esecuzione dell'azione
                print(f"ERRORE ESECUZIONE: {message_to_user}")
                action_history.append(f"FAILED_ACTION: {action_str}. Reason: {message_to_user}")
                # Potresti aggiungere un input per chiedere all'utente come procedere
                # user_resp = input("Azione fallita. Vuoi riprovare (r), modificare obiettivo (m), o uscire (e)? [r/m/e]: ") ...
            # In entrambi i casi, continua al prossimo ciclo
        
        if executed:
            action_history.append(f"EXECUTED_SUCCESS: {action_str}")
        elif not message_to_user : # Se non eseguito e non c'è messaggio (improbabile), segnala fallimento generico
            action_history.append(f"FAILED_ACTION_UNKNOWN_REASON: {action_str}")


        # Pausa più lunga tra i passi dell'agente per dare tempo alla GUI di aggiornarsi
        # e per permettere all'utente di osservare (e intervenire con Ctrl+C se necessario)
        print("   (In attesa che la GUI si stabilizzi...)")
        time.sleep(.5) # Aumentato a 2 secondi

    else: 
        print(f"\nRaggiunto il numero massimo di passi ({max_steps_per_goal}) per l'obiettivo.")

    print("\n--- Assistente GUI Terminato ---")



# --- FUNZIONI PER INTEGRAZIONE UI ---

def run_automation_task(goal_text, app=None, callback=None, max_steps=20):
    """
    Esegue un compito di automazione GUI utilizzando Gemini.
    Può essere chiamato dall'interfaccia utente di StudyWiz.
    
    Args:
        goal_text (str): L'obiettivo dell'automazione (es. "Apri blocco note e scrivi ciao")
        app (GUI, optional): Istanza della classe GUI per interazione con l'interfaccia
        callback (callable, optional): Funzione di callback per aggiornare l'UI durante l'esecuzione.
                                      Chiamata con (step_num, total_steps, action, status, message)
        max_steps (int): Numero massimo di passi per completare il compito
        
    Returns:
        dict: Dizionario con i risultati dell'operazione e la cronologia delle azioni
    """
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    
    action_history = []
    overall_goal = goal_text
    
    # Invia notifica iniziale tramite callback
    if callback:
        callback(0, max_steps, "START", "running", f"Inizializzazione automazione: '{overall_goal}'")
    elif app:
        app.post_message(f"🚀 Inizializzazione: '{overall_goal}'", is_sent=False)
    
    for step_count in range(max_steps):
        # Aggiorna progressione
        if callback:
            callback(step_count + 1, max_steps, "PROGRESS", "running", 
                    f"Passo {step_count + 1}/{max_steps}")
        
        current_elements, screenshot = capture_screen_and_extract_elements()
        screen_desc = describe_elements_for_llm(current_elements)
        
        # Ottieni azione da Gemini
        action_str = get_next_action_from_gemini(overall_goal, "\n".join(action_history[-5:]), screen_desc)
        
        if not action_str:
            if callback:
                callback(step_count + 1, max_steps, "ERROR", "error", 
                        "L'LLM non ha restituito un'azione valida")
            elif app:
                app.post_message("❌ L'AI non ha restituito un'azione valida", is_sent=False)
            action_history.append("SYSTEM_ERROR: LLM no action returned.")
            time.sleep(2)
            continue
        
        # Notifica l'azione che stiamo per eseguire
        if app:
            app.post_message(f"🤖 Eseguo: {action_str}", is_sent=False)
        
        # Esegui l'azione
        executed, message_to_user = execute_action(action_str, current_elements)
        
        if message_to_user == "DONE":
            if callback:
                callback(step_count + 1, max_steps, "DONE", "success", 
                        f"Obiettivo '{overall_goal}' completato!")
            elif app:
                app.post_message(f"✅ Obiettivo '{overall_goal}' completato!", is_sent=False)
            action_history.append("TASK_COMPLETED")
            break
        
        if message_to_user and not executed:
            if action_str.startswith("ASK_USER"):
                # Quando integrato nell'UI, chiedi all'utente tramite callback
                if callback:
                    callback(step_count + 1, max_steps, "ASK_USER", "waiting", message_to_user)
                elif app:
                    app.post_message(f"❓ {message_to_user}", is_sent=False)
                    # In modalità app, aspetta con timeout
                    time.sleep(3)  # Attesa simulata
                    action_history.append(f"USER_RESPONSE: Timeout in modalità UI")
                else:
                    # In modalità headless, va in timeout e salta
                    action_history.append(f"USER_QUESTION: \"{message_to_user}\" (Skipped in headless mode)")
            else:
                # Errore nell'esecuzione dell'azione
                if callback:
                    callback(step_count + 1, max_steps, "ERROR", "error", 
                           f"Errore: {message_to_user}")
                elif app:
                    app.post_message(f"❌ Errore: {message_to_user}", is_sent=False)
                action_history.append(f"FAILED_ACTION: {action_str}. Reason: {message_to_user}")
        
        if executed:
            if callback:
                callback(step_count + 1, max_steps, action_str, "success", 
                        f"Eseguito: {action_str}")
            elif app and step_count % 3 == 0:  # Notifica solo ogni 3 passi per non ingombrare la chat
                app.post_message(f"✅ Eseguito: {action_str}", is_sent=False)
            action_history.append(f"EXECUTED_SUCCESS: {action_str}")
        elif not message_to_user:
            if callback:
                callback(step_count + 1, max_steps, action_str, "error", 
                        "Fallito per motivo sconosciuto")
            elif app:
                app.post_message(f"❌ Azione fallita: {action_str}", is_sent=False)
            action_history.append(f"FAILED_ACTION_UNKNOWN_REASON: {action_str}")
        
        # Pausa per stabilizzazione della GUI
        time.sleep(0.5)
    
    else:
        if callback:
            callback(max_steps, max_steps, "TIMEOUT", "warning", 
                   f"Raggiunto il numero massimo di passi ({max_steps})")
        elif app:
            app.post_message(f"⚠️ Raggiunto il numero massimo di passi ({max_steps})", is_sent=False)
    
    result = {
        "completed": message_to_user == "DONE",
        "steps_executed": step_count + 1,
        "action_history": action_history,
        "goal": overall_goal
    }
    
    return result

def run_automation_async(goal_text, app=None, callback=None, max_steps=20):
    """
    Avvia l'automazione in un thread separato per non bloccare l'UI.
    
    Args:
        goal_text: L'obiettivo dell'automazione
        app: Istanza dell'app GUI
        callback, max_steps: Come in run_automation_task
    
    Returns:
        threading.Thread: Il thread che esegue l'automazione
    """
    def run_with_exception_handling():
        try:
            run_automation_task(goal_text, app, callback, max_steps)
        except Exception as e:
            import traceback
            error_message = f"Errore durante l'automazione: {str(e)}"
            print(error_message)
            print(traceback.format_exc())
            if app:
                app.post_message(f"❌ {error_message}", is_sent=False)

    automation_thread = threading.Thread(
        target=run_with_exception_handling
    )
    automation_thread.daemon = True
    automation_thread.start()
    return automation_thread

# Sostituisci il vecchio call_gemini_api con questa funzione
def call_gemini_api(prompt, app=None):
    """
    Versione compatibile con la vecchia funzione call_gemini_api.
    Ora supporta l'integrazione con l'app GUI StudyWiz.
    
    Args:
        prompt: L'obiettivo dell'automazione come stringa
        app: Istanza opzionale dell'app GUI di StudyWiz
    
    Returns:
        threading.Thread: Thread di automazione in esecuzione
    """
    print("="*30)
    print(" Assistente GUI Gemini - v0.3 (Integrato) ")
    print("="*30)
    print("Per interrompere PyAutoGUI: muovi rapidamente il mouse nell'angolo in alto a sinistra.")
    print("Premi Ctrl+C nel terminale per uscire dall'assistente.")

    # Lancia l'automazione con l'istanza dell'app (se fornita)
    return run_automation_async(prompt, app=app, max_steps=100)

def process_audio_command(audio_file, app=None):
    """
    Processa un comando vocale da un file audio.
    
    Args:
        audio_file (str): Percorso al file audio
        app (GUI, optional): Istanza dell'app GUI per interazione
    
    Returns:
        str: Testo riconosciuto o None in caso di errore
    """
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        
        # Converti audio in formato compatibile
        sound = AudioSegment.from_wav(audio_file)
        converted_file = audio_file.replace(".wav", "_converted.wav")
        sound.export(converted_file, format="wav")
        
        # Esegui il riconoscimento
        recognizer = sr.Recognizer()
        with sr.AudioFile(converted_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="it-IT")
            
        # Pulizia
        os.remove(converted_file)
        
        # Esegui l'automazione con il testo riconosciuto
        if app:
            app.post_message(f"🎤 Audio riconosciuto: '{text}'", is_sent=False)
            call_gemini_api(text, app=app)
            
        return text
        
    except Exception as e:
        print(f"Errore nel riconoscimento audio: {e}")
        if app:
            app.post_message(f"❌ Errore nel riconoscimento audio: {str(e)}", is_sent=False)
        return None