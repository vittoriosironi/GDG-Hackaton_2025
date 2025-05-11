import tkinter as tk
from tkinter import scrolledtext, Canvas, Frame, Text, PhotoImage
import datetime
import threading
import os
import pyaudio
import wave
import numpy as np
import time
import sys
import json
from pydub import AudioSegment
import speech_recognition as sr

import rumps
MENU_BAR_AVAILABLE = True

# Fix the import by adding the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import functions
AUTOMATION_AVAILABLE = True



# Aggiungi queste importazioni per la registrazione audio
try:
    import pyaudio
    import wave
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Librerie audio non disponibili. La registrazione verrà simulata.")
    
# Menu bar implementation for macOS


class MicrophoneButton(tk.Canvas):
    def __init__(self, parent, command=None, **kwargs):
        self.command = command
        self.is_recording = False
        height = kwargs.pop('height', 40)
        width = kwargs.pop('width', 40)
        bg_color = kwargs.pop('bg', '#ffffff')
        hover_bg = kwargs.pop('hover_bg', '#dddddd')
        self.active_bg = kwargs.pop('active_bg', '#ff0000')  # Colore durante la registrazione
        
        super().__init__(parent, height=height, width=width, 
                         bg="#e0e0e0", highlightthickness=0, **kwargs)
        
        # Disegna il background arrotondato
        self.normal_bg = bg_color
        self.hover_bg = hover_bg
        
        # Crea il background circolare
        self.background = self.create_rectangle(0, 0, width, height, 
                                              fill=self.normal_bg, outline="", 
                                              width=0, radius=width//2)
        
        # Carica l'immagine del microfono dalla cartella resources
        try:
            # Percorso assoluto al file della directory corrente
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Vai alla directory principale del progetto
            project_dir = os.path.dirname(current_dir)
            # Percorso dell'immagine del microfono nella cartella resources
            image_path = os.path.join(project_dir, "resources", "microphone.png")
            
            if os.path.exists(image_path):
                # Carica l'immagine
                self.image = PhotoImage(file=image_path)
                
                # Ridimensiona l'immagine se necessario
                scale_factor = min(width/self.image.width(), height/self.image.height()) * 0.6
                if scale_factor < 1:
                    # Ridimensiona l'immagine se è troppo grande
                    self.image = self.image.subsample(int(1/scale_factor))
                elif scale_factor > 1:
                    # Ingrandisci l'immagine se è troppo piccola
                    self.image = self.image.zoom(int(scale_factor))
                
                # Crea l'immagine nel canvas
                self.image_item = self.create_image(width//2, height//2, image=self.image)
            else:
                print(f"Immagine non trovata: {image_path}")
                self._create_mic_icon()
        except Exception as e:
            print(f"Errore nel caricamento dell'immagine: {e}")
            # Fallback se c'è un errore di caricamento
            self._create_mic_icon()
        
        # Binding degli eventi per la registrazione continua
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _create_mic_icon(self):
        """Crea un'icona microfono usando le primitive di disegno."""
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        
        # Disegna un microfono stilizzato
        # Base del microfono
        self.create_rectangle(width//2-5, height//2+5, width//2+5, height//2+8, 
                            fill="white", outline="")
        
        # Stelo del microfono
        self.create_rectangle(width//2-1, height//2, width//2+1, height//2+8, 
                            fill="white", outline="")
        
        # Testa del microfono
        self.create_oval(width//2-6, height//2-8, width//2+6, height//2+2, 
                       fill="white", outline="")
    
    def _on_press(self, event):
        # Inizia la registrazione
        self.is_recording = True
        self.itemconfig(self.background, fill=self.active_bg)
        if self.command:
            self.command(True)  # Passa True per indicare l'inizio della registrazione
    
    def _on_release(self, event):
        # Termina la registrazione
        if self.is_recording:
            self.is_recording = False
            self.itemconfig(self.background, fill=self.normal_bg)
            if self.command:
                self.command(False)  # Passa False per indicare la fine della registrazione
    
    def _on_enter(self, event):
        # Cambia colore quando il mouse entra (solo se non sta registrando)
        if not self.is_recording:
            self.itemconfig(self.background, fill=self.hover_bg)
    
    def _on_leave(self, event):
        # Ripristina il colore originale quando il mouse esce (solo se non sta registrando)
        if not self.is_recording:
            self.itemconfig(self.background, fill=self.normal_bg)
    
    def create_rectangle(self, x1, y1, x2, y2, **kwargs):
        """
        Crea un rettangolo con angoli arrotondati.
        """
        radius = kwargs.pop('radius', 0)
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

# Aggiungi una classe per gestire la registrazione audio
class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.audio_thread = None
        self.frames = []
        self.sample_format = pyaudio.paInt16 if AUDIO_AVAILABLE else None
        self.channels = 1
        self.fs = 44100  # Frequenza di campionamento
        self.chunk = 1024  # Dimensione dei frame
        self.audio = pyaudio.PyAudio() if AUDIO_AVAILABLE else None
        
        # Crea una directory temporanea per salvare le registrazioni audio
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def start_recording(self):
        """Inizia la registrazione in un thread separato."""
        if not AUDIO_AVAILABLE:
            print("Simulazione registrazione audio...")
            self.recording = True
            return
            
        self.frames = []
        self.recording = True
        self.audio_thread = threading.Thread(target=self._record)
        self.audio_thread.daemon = True
        self.audio_thread.start()
    
    def stop_recording(self):
        """Termina la registrazione e salva il file audio."""
        if not AUDIO_AVAILABLE:
            print("Simulazione registrazione audio terminata.")
            self.recording = False
            return None
            
        if self.recording:
            self.recording = False
            if self.audio_thread:
                self.audio_thread.join()
            
            # Salva la registrazione in un file temporaneo
            filename = os.path.join(self.temp_dir, f"rec_{int(time.time())}.wav")
            
            try:
                wf = wave.open(filename, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.sample_format))
                wf.setframerate(self.fs)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                return filename
            except Exception as e:
                print(f"Errore nel salvare il file audio: {e}")
                return None
        return None
    
    def _record(self):
        """Registra l'audio dal microfono."""
        try:
            stream = self.audio.open(format=self.sample_format,
                                channels=self.channels,
                                rate=self.fs,
                                frames_per_buffer=self.chunk,
                                input=True)
            
            while self.recording:
                data = stream.read(self.chunk)
                self.frames.append(data)
            
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Errore durante la registrazione: {e}")
            self.recording = False
    
    def close(self):
        """Chiude correttamente l'istanza di PyAudio."""
        if AUDIO_AVAILABLE and self.audio:
            self.audio.terminate()

        
class RoundedEntry(tk.Canvas):
    def __init__(self, parent, **kwargs):
        height = kwargs.pop('height', 40)
        width = kwargs.pop('width', 400)
        bg_color = kwargs.pop('bg', '#DDDDDD')
        fg_color = kwargs.pop('fg', '#DDDDDD')
        font = kwargs.pop('font', ('Helvetica', 11))
        
        super().__init__(parent, height=height, width=width, 
                          bg="#DDDDDD", highlightthickness=0, **kwargs)
        
        # Disegna il background arrotondato
        self.background = self.create_rectangle(10, 5, width-10, height-5, 
                                               fill=bg_color, outline="", 
                                               width=0, radius=20)
        
        # Crea l'entry sopra il canvas
        self.entry = tk.Entry(self, font=font, bg=bg_color, fg=fg_color,
                              relief=tk.FLAT, highlightthickness=0)
        self.entry_window = self.create_window(width//2, height//2, 
                                              window=self.entry, width=width-30)
    
    def get(self):
        return self.entry.get()
    
    def delete(self, first, last):
        return self.entry.delete(first, last)
    
    def bind(self, event, callback):
        return self.entry.bind(event, callback)
    
    def focus_set(self):
        return self.entry.focus_set()
    
    def create_rectangle(self, x1, y1, x2, y2, **kwargs):
        radius = kwargs.pop('radius', 0)
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, **kwargs):
        self.command = command
        height = kwargs.pop('height', 40)
        width = kwargs.pop('width', 100)
        bg_color = kwargs.pop('bg', '#0078FF')
        fg_color = kwargs.pop('fg', 'white')
        font = kwargs.pop('font', ('Helvetica', 10, 'bold'))
        radius = kwargs.pop('radius', 15)
        
        super().__init__(parent, height=height, width=width, 
                        bg="#e0e0e0", highlightthickness=0, **kwargs)
        
        # Disegna il background arrotondato
        self.normal_bg = bg_color
        self.hover_bg = "#0069E0"  # Colore quando il mouse è sopra
        
        self.background = self.create_rectangle(0, 0, width, height, 
                                              fill=self.normal_bg, outline="", 
                                              width=0, radius=radius)
        
        # Testo del pulsante
        self.text_id = self.create_text(width//2, height//2, text=text, 
                                      fill=fg_color, font=font)
        
        # Binding degli eventi
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
    def _on_enter(self, event):
        # Cambia colore quando il mouse entra
        self.itemconfig(self.background, fill=self.hover_bg)
    
    def _on_leave(self, event):
        # Ripristina il colore originale quando il mouse esce
        self.itemconfig(self.background, fill=self.normal_bg)
    
    def _on_click(self, event):
        # Esegue il comando quando viene cliccato
        if self.command:
            self.command()
            
    def create_rectangle(self, x1, y1, x2, y2, **kwargs):
        radius = kwargs.pop('radius', 0)
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

class BubbleCanvas(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#ffffff", **kwargs)
        self.canvas = tk.Canvas(self, bg="#ffffff", bd=0, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame interno scrollabile
        self.inner_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.vsb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Per tenere traccia dell'altezza attuale
        self.current_y = 10
        
        # Colori per i messaggi
        self.SENT_BG = "#0078FF"
        self.RECEIVED_BG = "#E5E5EA"
        self.TEXT_COLOR_SENT = "white"
        self.TEXT_COLOR_RECEIVED = "black"
    
    def _on_frame_configure(self, event):
        # Aggiorna la regione scrollabile
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        # Quando il canvas è ridimensionato, ridimensiona anche il frame interno
        width = event.width
        self.canvas.itemconfig(self.canvas_window, width=width)
    
    def create_rounded_bubble(self, parent, text, bg_color, fg_color, is_sent):
        """
        Crea un messaggio con bordi arrotondati.
        """
        # Creiamo un canvas con sfondo trasparente
        width = 250
        height = 0
        
        # Calcola l'altezza necessaria per il testo
        temp_label = tk.Label(parent, text=text, wraplength=260, font=("Helvetica", 10))
        temp_label.pack()
        parent.update()
        height = temp_label.winfo_reqheight() + 20  # Aggiunge padding
        temp_label.destroy()
        
        # Crea il canvas
        bubble = tk.Canvas(parent, width=width, height=height, bg="#ffffff", 
                        highlightthickness=0)
        
        # Disegna il rettangolo arrotondato
        radius = 15  # Raggio degli angoli arrotondati
        
        # Utilizza archi per creare angoli più belli e uniformi
        # Forma del rettangolo arrotondato
        bubble.create_rectangle(radius, 0, width-radius, height, 
                            fill=bg_color, outline="")  # Rettangolo centrale
        bubble.create_rectangle(0, radius, width, height-radius, 
                            fill=bg_color, outline="")  # Rettangolo verticale
        
        # Angoli arrotondati (archi)
        bubble.create_arc(0, 0, 2*radius, 2*radius, 
                        start=90, extent=90, fill=bg_color, outline="")  # Alto sinistra
        bubble.create_arc(width-2*radius, 0, width, 2*radius, 
                        start=0, extent=90, fill=bg_color, outline="")  # Alto destra
        bubble.create_arc(width-2*radius, height-2*radius, width, height, 
                        start=270, extent=90, fill=bg_color, outline="")  # Basso destra
        bubble.create_arc(0, height-2*radius, 2*radius, height, 
                        start=180, extent=90, fill=bg_color, outline="")  # Basso sinistra
        
       
        
        # Aggiungi il testo
        text_item = bubble.create_text((width)/2, height/2, text=text, fill=fg_color, 
                                    font=("Helvetica", 10), width=230, 
                                    justify=tk.LEFT)
        
        return bubble
    
    def add_bubble(self, message, timestamp, is_sent=True):
        # Crea un frame per il messaggio
        bubble_frame = tk.Frame(self.inner_frame, bg="#ffffff")
        bubble_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Seleziona i colori in base al tipo di messaggio
        if is_sent:
            bg_color = self.SENT_BG
            fg_color = self.TEXT_COLOR_SENT
            align = tk.RIGHT
        else:
            bg_color = self.RECEIVED_BG
            fg_color = self.TEXT_COLOR_RECEIVED
            align = tk.LEFT
        
        # Crea la bolla di messaggio arrotondata
        bubble = self.create_rounded_bubble(bubble_frame, message, bg_color, fg_color, is_sent)
        bubble.pack(side=align, pady=2)
        
        # Aggiungi un piccolo timestamp sotto il messaggio (opzionale)
        if timestamp:
            time_label = tk.Label(bubble_frame, text=timestamp, font=("Helvetica", 7), 
                                 fg="#888888", bg="#ffffff")
            time_label.pack(side=align, padx=5)
        
        # Scroll fino in fondo
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
        
        self.current_y += bubble_frame.winfo_reqheight() + 10
        
    def remove_last_bubble(self):
        """
        Rimuove l'ultima bolla di messaggio aggiunta all'interfaccia.
        
        Returns:
            bool: True se un messaggio è stato rimosso, False altrimenti
        """
        # Ottiene tutti i widget frame che contengono le bolle
        frames = self.inner_frame.winfo_children()
        
        # Se ci sono bolle, rimuove l'ultima
        if frames:
            last_frame = frames[-1]
            # Aggiorna l'altezza sottraendo quella del frame rimosso
            self.current_y -= last_frame.winfo_reqheight() + 10
            # Distrugge il widget
            last_frame.destroy()
            
            # Aggiorna la regione scrollabile
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            return True
        
        return False
        



# Modify GUI class to support menu bar
class GUI:
    def __init__(self, title="StudyWiz", width=500, height=600):
        # Definisci i colori qui per evitare variabili globali
        self.SENT_BG = "#0078FF"
        self.RECEIVED_BG = "#E5E5EA"
        self.TEXT_COLOR_SENT = "white"
        self.TEXT_COLOR_RECEIVED = "black"
        self.ACCENT_COLOR = "black"
        
        # Salva le dimensioni
        self.width = width
        self.height = height
        self.title = title
        
        # Definisci la variabile root qui, ma la inizializzeremo in start()
        self.root = None
        self.message_area = None
        self.message_input = None
        
        # Inizializza il registratore audio
        self.audio_recorder = AudioRecorder() if AUDIO_AVAILABLE else None
        
        # Flag per il thread
        self.is_running = False
        
        # Menu bar app
        self.menu_bar_app = None
        self.menu_bar_thread = None
        
        # Initialize Gemini API (will be used when the GUI starts)
        self.model = None
    
    def setup_ui(self):
            # Initialize Gemini
        try:
            self.model = functions.configure_gemini()
        except Exception as e:
            print(f"Error initializing Gemini API: {e}")
        # Creazione della finestra principale
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.configure(bg="#ffffff")
        
        # Imposta un'icona per la finestra
        try:
            # Percorso assoluto al file della directory corrente
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Vai alla directory principale del progetto
            project_dir = os.path.dirname(current_dir)
            # Percorso dell'icona nella cartella resources
            icon_path = os.path.join(project_dir, "resources", "icon.png")
            
            if os.path.exists(icon_path):
                # Crea un'icona per la finestra
                icon = PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
                
                # Setup menu bar app if available
                if MENU_BAR_AVAILABLE:
                    self._setup_menu_bar(icon_path)
            else:
                print(f"Icona non trovata: {icon_path}")
        except Exception as e:
            print(f"Errore nel caricamento dell'icona: {e}")
        
        # Frame principale
        main_frame = tk.Frame(self.root, bg="#ffffff")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header con logo
        header_frame = tk.Frame(main_frame, bg="#FFFFFF", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Ombra sotto l'header
        shadow_frame = tk.Frame(main_frame, height=2, bg="#FFFFFF")
        shadow_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Logo
        logo_label = tk.Label(header_frame, text="StudyWiz", font=("Arial", 20, "bold"), 
                           fg=self.ACCENT_COLOR, bg="#FFFFFF")
        logo_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Sottotitolo
        subtitle_label = tk.Label(header_frame, text="25:09", 
                               font=("Arial", 15), fg="#888888", bg="#FFFFFF")
        subtitle_label.pack(side=tk.RIGHT, padx=25, pady=15)
        
        # Area messaggi (scrollable con bolle)
        self.message_area = BubbleCanvas(main_frame)
        self.message_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame per l'area di input del messaggio
        input_frame = tk.Frame(main_frame, bg="#e0e0e0")
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        # Campo di input per il messaggio con bordi arrotondati
        self.message_input = RoundedEntry(input_frame, width=350, height=40, 
                                      bg="#FFFFFF", fg="#333333", font=("Helvetica", 11))
        self.message_input.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.message_input.bind("<Return>", self._send_message)
        
        # Pulsante microfono circolare con registrazione continua
        mic_button = MicrophoneButton(input_frame, command=self._handle_recording, 
                               bg=self.SENT_BG, hover_bg="#0069E0", active_bg="#ff4040", width=40, height=40)
        mic_button.pack(side=tk.RIGHT)
        
        # Aggiungi alcuni messaggi di esempio
        self.message_area.add_bubble("Ciao! Benvenuto in StudyWiz!", "09:16", is_sent=False)
        self.message_area.add_bubble("Come posso aiutarti?", "09:18", is_sent=False)
        
        # Focus iniziale sull'input
        self.message_input.focus_set()
        
        # Configure minimize behavior to hide to menu bar instead of minimizing
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _setup_menu_bar(self, icon_path):
        """Setup the menu bar application."""
        if MENU_BAR_AVAILABLE:
            try:
                # Create a separate process for the menu bar app instead of a thread
                import subprocess
                import sys
                
                # Create a simple script for the menu bar app
                menu_bar_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu_bar_app.py")
                
 
                
                # Launch the menu bar app in a separate process
                self.menu_bar_process = subprocess.Popen([sys.executable, menu_bar_script, icon_path])
                
                # Set up periodic check for communication from the menu bar app
                self.root.after(1000, self._check_menu_bar_signals)
                
            except Exception as e:
                import traceback
                print(f"Error setting up menu bar: {e}")
                traceback.print_exc()

    def _check_menu_bar_signals(self):
        """Check for signals from the menu bar app."""
        try:
            # Check if the menu bar app wants to show the main window
            if os.path.exists("/tmp/studywiz_show"):
                os.remove("/tmp/studywiz_show")
                self.root.deiconify()
                self.root.lift()
                
            # Check if the menu bar app wants to quit
            if os.path.exists("/tmp/studywiz_quit"):
                os.remove("/tmp/studywiz_quit")
                self._on_close()
                return
                
        except Exception as e:
            print(f"Error checking menu bar signals: {e}")
        
        # Continue checking if the app is still running
        if self.is_running and self.root:
            self.root.after(1000, self._check_menu_bar_signals)

    def _on_close(self):
        """Gestisce la chiusura dell'applicazione."""
        if self.audio_recorder:
            self.audio_recorder.close()
        self.is_running = False
        
        # Terminate the menu bar process if it exists
        if hasattr(self, 'menu_bar_process') and self.menu_bar_process:
            try:
                self.menu_bar_process.terminate()
            except Exception as e:
                print(f"Error terminating menu bar process: {e}")
        
        if self.root:
            self.root.destroy()
    
    def _on_window_close(self):
        """Handle window close event - hide to menu bar instead of closing."""
        if MENU_BAR_AVAILABLE and self.menu_bar_app:
            # Hide the window instead of closing
            self.root.withdraw()
        else:
            # If no menu bar support, close normally
            self._on_close()
    
    def _handle_recording(self, is_start):
        """
        Gestisce l'inizio e la fine della registrazione audio.
        Quando l'audio termina, lo invia a Gemini per l'elaborazione.
        
        Args:
            is_start (bool): Se True, inizia la registrazione; se False, la termina
        """
        if is_start:
            # Inizia la registrazione
            timestamp = datetime.datetime.now().strftime("%H:%M")
            self.message_area.add_bubble("Sto registrando...", timestamp, is_sent=True)
            
            if self.audio_recorder:
                self.audio_recorder.start_recording()
        else:
            # Termina la registrazione
            timestamp = datetime.datetime.now().strftime("%H:%M")
            self.message_area.remove_last_bubble()
            
            if self.audio_recorder:
                audio_file = self.audio_recorder.stop_recording()
                
                if audio_file:
                    self.message_area.add_bubble(f"Messaggio vocale inviato", 
                                        timestamp, is_sent=True)
                    
                    # Mostra messaggio di elaborazione
                    self.message_area.add_bubble(
                        "Ho ricevuto il tuo messaggio vocale! Sto elaborando...", 
                        datetime.datetime.now().strftime("%H:%M"), 
                        is_sent=False)
                    
                    # Avvia l'elaborazione audio in un thread separato
                    threading.Thread(target=self._process_audio_for_gemini, args=(audio_file,)).start()
                else:
                    self.message_area.add_bubble("Registrazione audio completata ma nessun file salvato", 
                                        timestamp, is_sent=True)
                    self.message_area.add_bubble(
                        "Non ho potuto elaborare l'audio. Riprova o digita il tuo messaggio.", 
                        datetime.datetime.now().strftime("%H:%M"), 
                        is_sent=False)

    def _process_audio_for_gemini(self, audio_file):
        """
        Process audio file for Gemini.
        
        1. Convert audio to text using speech recognition
        2. Send recognized text to functions.py for Gemini processing
        
        Args:
            audio_file (str): Path to audio file
        """
        recognized_text = None
        
        # Try to convert audio to text
        try:
            from pydub import AudioSegment
            import speech_recognition as sr
            
            # Convert from WAV to optimized format
            sound = AudioSegment.from_wav(audio_file)
            
            # Save in format optimized for SpeechRecognition
            converted_file = audio_file.replace(".wav", "_converted.wav")
            sound.export(converted_file, format="wav")
            
            # Recognize text from audio
            recognizer = sr.Recognizer()
            with sr.AudioFile(converted_file) as source:
                # Adjust for ambient noise to improve recognition
                recognizer.adjust_for_ambient_noise(source)
                audio_data = recognizer.record(source)
                
                try:
                    # Try using Google's speech recognition
                    recognized_text = recognizer.recognize_google(audio_data, language="en-US")
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    self.post_message("I couldn't understand what you said. Please try speaking more clearly.", is_sent=False)
                except sr.RequestError as e:
                    # API was unreachable or unresponsive
                    self.post_message(f"Google Speech Recognition service error: {e}", is_sent=False)
            
            # Clean up files regardless of success/failure
            try:
                # Remove temporary file
                if os.path.exists(converted_file):
                    os.remove(converted_file)
                
                # Also remove original audio file to save space
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception as e:
                print(f"Error removing temporary files: {e}")
                
        except ImportError as e:
            self.post_message(f"⚠️ Required libraries not available: {e}", is_sent=False)
            return
        except Exception as e:
            self.post_message(f"⚠️ Error processing audio: {str(e)}", is_sent=False)
            print(f"Audio processing error: {e}")
            return
        
        # Show recognized text and process with Gemini if recognition was successful
        if recognized_text:
            self.post_message(f"📝 I transcribed: \"{recognized_text}\"", is_sent=False)
            
            # Short pause before sending to Gemini
            time.sleep(1)
            
            # Process the recognized text using functions.py
            try:
                # Show a "thinking" message
                self.message_area.add_bubble(
                    "Processing your request...",
                    datetime.datetime.now().strftime("%H:%M"),
                    is_sent=False
                )
                
                # Process the user input using functions.py
                functions.process_user_input(recognized_text, self.handle_gemini_response)
                
            except Exception as e:
                self.message_area.remove_last_bubble()
                self.post_message(f"Error processing your request: {str(e)}", is_sent=False)
                print(f"Gemini processing error: {e}")
        else:
            self.post_message("❌ I couldn't understand the audio. Please try again or type your message.", is_sent=False)
    
    def _send_message(self, event=None):
        message = self.message_input.get()
        if message.strip():
            # Ottieni timestamp corrente
            timestamp = datetime.datetime.now().strftime("%H:%M")
            
            # Aggiungi il messaggio con stile a bolla
            self.message_area.add_bubble(message, timestamp, is_sent=True)
            
            self.run_automation(message)
            
            # Pulisci l'input
            self.message_input.delete(0, tk.END)
        
        return "break"  # Previene l'inserimento del newline
    
    def _mainloop(self):
        # Configura l'interfaccia utente
        self.setup_ui()
        
        # Avvia il mainloop di tkinter
        self.is_running = True
        self.root.mainloop()
        self.is_running = False
    
    def _on_close(self):
        """Gestisce la chiusura dell'applicazione."""
        if self.audio_recorder:
            self.audio_recorder.close()
        self.is_running = False
        
        # Close menu bar app if it's running
        if MENU_BAR_AVAILABLE and self.menu_bar_app:
            rumps.quit_application()
            
        if self.root:
            self.root.destroy()
    
    def start(self, threaded=False):
        """
        Avvia l'interfaccia grafica.
        
        Args:
            threaded (bool): Se True, avvia l'interfaccia in un thread separato
        """
        if threaded:
            # Avvia in un thread separato
            gui_thread = threading.Thread(target=self._mainloop)
            gui_thread.daemon = True  # Termina quando il thread principale termina
            gui_thread.start()
            return gui_thread
        else:
            # Avvia nel thread principale (bloccante)
            self._mainloop()
    
    def post_message(self, message, is_sent=False):
        """
        Aggiunge un messaggio all'interfaccia.
        
        Args:
            message (str): Il messaggio da visualizzare
            is_sent (bool): Se True, il messaggio appare come inviato dall'utente,
                           altrimenti come ricevuto dall'AI
        """
        if not self.is_running or not self.message_area:
            return False
        
        # Ottieni timestamp corrente
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # Usa after per aggiungere il messaggio in modo thread-safe
        self.root.after(0, lambda: self.message_area.add_bubble(message, timestamp, is_sent=is_sent))
        return True
    # Add this new method to your GUI class:

    def handle_gemini_response(self, response_text):
        """
        Callback function for Gemini responses
        
        Args:
            response_text (str): The response from Gemini
        """
        try:
            # First, try to find and extract JSON content
            json_start = response_text.find('```json')
            if json_start != -1:
                # Find the closing ```
                json_end = response_text.find('```', json_start + 7)
                if json_end != -1:
                    # Extract the JSON content
                    json_content = response_text[json_start + 7:json_end].strip()
                    try:
                        response_data = json.loads(json_content)
                        
                        if isinstance(response_data, dict):
                            action = response_data.get('action')
                            if action == 'timer':
                                minutes = response_data.get('minutes')
                                if minutes is not None:
                                    try:
                                        minutes = int(minutes)
                                        if minutes > 0:
                                            self.post_message(f"I've started a timer for {minutes} minutes. I'll let you know when it's time!")
                                        else:
                                            self.post_message("I'm sorry, but the timer duration needs to be a positive number. Could you please specify how many minutes you'd like to set the timer for?")
                                    except ValueError:
                                        self.post_message("I couldn't understand the timer duration. Could you please specify a number of minutes? For example: 'set a timer for 25 minutes'")
                            elif action == 'start_analysis':
                                self.post_message("I've started tracking your activity. I'll keep an eye on how you're spending your time and provide insights when you're ready!")
                            elif action == 'end_analysis':
                                self.post_message("I've stopped tracking your activity. You can check the insights in the log files.")
                            else:
                                self.post_message("I received an unknown action from Gemini. Please try your command again.")
                        return
                    except json.JSONDecodeError:
                        # If JSON parsing fails, fall back to regular message
                        pass
            
            # If we didn't find JSON or JSON parsing failed, look for a regular message
            message_start = response_text.find('```message')
            if message_start != -1:
                # Find the closing ```
                message_end = response_text.find('```', message_start + 9)
                if message_end != -1:
                    # Extract the message content
                    message_content = response_text[message_start + 9:message_end].strip()
                    self.post_message(message_content)
                    return
            
            # If we get here, we didn't find any special format, so treat the whole response as a message
            self.post_message(response_text)
            
        except Exception as e:
            self.post_message(f"Error processing Gemini response: {str(e)}")
        
        # Remove the "thinking" message (assuming it's the last bubble)
        self.message_area.remove_last_bubble()
        
        # Post the actual response
        #self.post_message(response_text, is_sent=False)
    
    def run_automation(self, goal_text):
        """
        Process user input using functions.py to interact with Gemini
        
        Args:
            goal_text (str): The user's input to process
        """
        def callback(response_text):
            self.handle_gemini_response(response_text)
            
        # Show a "thinking" message
        self.message_area.add_bubble(
            "Elaborazione in corso...",
            datetime.datetime.now().strftime("%H:%M"),
            is_sent=False
        )
        
        try:
            # Process the user input using functions.py
            functions.process_user_input(goal_text, self.handle_gemini_response)
        except Exception as e:
            self.message_area.add_bubble(
                f"Errore durante l'elaborazione: {str(e)}",
                datetime.datetime.now().strftime("%H:%M"),
                is_sent=False
            )
    
    
    
# Solo per test - questo codice viene eseguito solo se gui.py è eseguito direttamente
app = GUI(title="StudyWiz Test")
if __name__ == "__main__":
    # Crea e avvia l'interfaccia
    app.start()

