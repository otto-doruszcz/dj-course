import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import pyaudio
import wave
import os
import time
import threading
import queue
import sys
import logging
import logging.handlers
from typing import TextIO
from datetime import datetime
from history_manager import HistoryManager

# --- Global Configuration ---
APP_TITLE = "Azor Transcriber"
# Set to True to print output to the console (standard output/stderr).
VERBOSE = False
LOG_FILENAME = "transcriber.log"

# --- Logging Setup ---
class StreamToLogger(TextIO):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    This captures stdout/stderr, including print() statements.
    """
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        # Handle buffer and write line by line
        for line in buf.rstrip().splitlines():
            # Check if the line is not empty (prevents logging empty lines from print())
            if line.strip():
                self.logger.log(self.level, line.strip())

    def flush(self):
        # Required by TextIO interface, but we flush line-by-line in write
        pass

# Configure the global logger BEFORE application startup
def setup_logging():
    """Con gures the logging system to save all output to a le and optionally to console."""
    os.makedirs('output', exist_ok=True)
    
    # 1. Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Capture everything from INFO level up

    # 2. File Handler (Always active)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, 
        maxBytes=1024*1024*5, # 5 MB per file
        backupCount=5,
        encoding='utf-8'
    )
    # Define a simple formatter for the file
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 3. Console Handler (Only active if VERBOSE is True)
    if VERBOSE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 4. Redirect stdout and stderr to the logger
    sys.stdout = StreamToLogger(root_logger, logging.INFO)
    sys.stderr = StreamToLogger(root_logger, logging.ERROR)

setup_logging()
logging.info("Application initialization started.")

# --- Whisper Dependencies ---
# Ensure you have installed: pip install torch transformers librosa
# (Librosa might require ffmpeg)
try:
    import torch
    from transformers import pipeline
except ImportError:
    logging.error("ERROR: 'transformers' or 'torch' libraries not found.")
    logging.error("Install them using: pip install torch transformers")
    exit()

# === 1. Transcription Configuration ===
MODEL_NAME = "openai/whisper-tiny"

def output_filename()  -> tuple:
    """
    Generates output filename for transcription results.

    Returns:
        Tuple of (filepath, timestamp_string) for history tracking
    """
    os.makedirs('output/recordings', exist_ok=True)
    timestamp_int = int(time.time() * 1000)  # millisecond precision
    timestamp_iso = datetime.utcnow().isoformat() + "Z"
    return f"output/recordings/recording-{timestamp_int}.wav", timestamp_iso

def transcribe_audio(audio_path: str, model_name: str) -> str:
    """
    Loads the Whisper model and transcribes the audio file.
    This function is blocking and should be run in a separate thread.
    """
    try:
        logging.info(f"Loading model: {model_name}...")
        # Initialize pipeline
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logging.info(f"Using device: {device}")
        
        asr_pipeline = pipeline(
            "automatic-speech-recognition", 
            model=model_name,
            device=device
        )

        logging.info(f"Starting transcription for file: {audio_path}...")
        result = asr_pipeline(audio_path)
        
        transcription = result["text"].strip()
        
        logging.info("Transcription finished.")
        return transcription

    except FileNotFoundError:
        logging.error(f"ERROR: Audio file not found at path: {audio_path}")
        return f"ERROR: Audio file not found at path: {audio_path}"
    except Exception as e:
        logging.error(f"An unexpected error occurred during transcription: {e}", exc_info=True)
        return f"An unexpected error occurred during transcription: {e}"


# === 2. Recording Configuration ===
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Standard for speech models (Whisper)
MAX_RECORD_DURATION = 30 # Maximum recording length in seconds

# === 3. Tkinter GUI Application ===
class AudioRecorderApp:
    def __init__(self, master):
        self.master = master
        
        # 1. Set application title (window title)
        master.title(APP_TITLE)
        
        # 2. Set the application name for the OS/taskbar
        # This is cross-platform attempt to set the application name
        try:
            # For macOS and some X11 environments
            self.master.tk.call('wm', 'iconname', self.master._w, APP_TITLE)
        except tk.TclError:
            # Standard method, usually works on Windows/Linux
            self.master.wm_iconname(APP_TITLE)
            
        master.geometry("600x450") # Slightly larger window
        master.config(bg="#121212") # Set dark background for root

        # --- TKINTER WIDGET STYLES (ttk) ---
        style = ttk.Style()
        style.theme_use('default') 

        # Configure the dark background for the Notebook tabs
        style.configure('TNotebook', background='#121212', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1E1E1E', foreground='white', borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', '#0F0F0F')], foreground=[('selected', 'white')])

        # 1. Define new style for dark gray buttons
        style.configure('Dark.TButton',
                        background='#333333',    
                        foreground='white',     
                        font=('Arial', 14),
                        bordercolor='#333333',
                        borderwidth=0,
                        focuscolor='#333333',
                        padding=(20, 10, 20, 10) 
                       )
        
        # 2. Define button appearance in different states (active/disabled)
        style.map('Dark.TButton',
                  background=[('active', '#555555'), # Lighter gray for hover/active state
                              ('disabled', '#333333')], # Disabled state uses the default background
                 )

        logging.info("GUI initialization started.")

        # Initialize HistoryManager for persistent transcription history
        self.history_manager = HistoryManager()

        # Initialize PyAudio
        try:
            self.p = pyaudio.PyAudio()
        except Exception as e:
            logging.critical(f"Could not initialize PyAudio: {e}. Destroying GUI.")
            messagebox.showerror("PyAudio Error", f"Could not initialize PyAudio: {e}\nDo you have 'portaudio' installed?")
            master.destroy()
            return
            
        self.frames = []
        self.stream = None
        self.recording = False
        self.start_time = None
        self.record_timer_id = None
        self.current_timestamp = None  # Track timestamp for current recording

        # Queue for inter-thread communication
        self.transcription_queue = queue.Queue()
        
        # --- TAB MENU SETUP (Notebook) ---
        self.notebook = ttk.Notebook(master, style='TNotebook')
        self.notebook.pack(pady=10, padx=10, fill='both', expand=True)

        # 1. Transcriber Tab
        self.transcriber_frame = tk.Frame(self.notebook, bg="#121212") # Set dark background for frame
        self.notebook.add(self.transcriber_frame, text='Transcriber')

        # 2. History Tab
        self.history_frame = tk.Frame(self.notebook, bg="#121212") # Consistent dark background
        self.notebook.add(self.history_frame, text='Transcription History')
        
        # Top label
        tk.Label(self.history_frame, text="Transcription History", font=('Arial', 14, 'bold'), fg='white', bg="#121212").pack(pady=(10, 5))

        # Create frame for the table and scrollbar
        table_frame = tk.Frame(self.history_frame, bg="#121212")
        table_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Create Treeview table with columns
        self.history_tree = ttk.Treeview(
            table_frame,
            columns=("timestamp", "duration", "preview"),
            height=12,
            show="headings"
        )

        # Define column headings
        self.history_tree.heading("timestamp", text="Timestamp")
        self.history_tree.heading("duration", text="Duration")
        self.history_tree.heading("preview", text="Preview Text")

        # Define column widths
        self.history_tree.column("timestamp", width=150)
        self.history_tree.column("duration", width=80)
        self.history_tree.column("preview", width=400)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)

        # Pack table and scrollbar
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Bind events for row interaction
        self.history_tree.bind('<Double-1>', self._on_history_row_double_click)
        self.history_tree.bind('<Delete>', self._on_history_delete_key)

        # Bottom button frame
        button_frame = tk.Frame(self.history_frame, bg="#121212")
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        refresh_button = ttk.Button(
            button_frame,
            text="Refresh",
            command=self._refresh_history_display,
            style='Dark.TButton'
        )
        refresh_button.pack(side=tk.LEFT, padx=5)

        delete_button = ttk.Button(
            button_frame,
            text="Delete Selected",
            command=self._delete_selected_history,
            style='Dark.TButton'
        )
        delete_button.pack(side=tk.LEFT, padx=5)

        # Configure Treeview colors for dark theme
        style.configure('Treeview', background='#1E1E1E', foreground='white', fieldbackground='#1E1E1E')
        style.map('Treeview', background=[('selected', '#0F0F0F')])
        style.configure('Treeview.Heading', background='#333333', foreground='white')
        style.map('Treeview.Heading', background=[('active', '#555555')])

        # Initial load of history
        self._refresh_history_display()



        # 3. Settings Tab
        self.settings_frame = tk.Frame(self.notebook, bg="#121212") 
        self.notebook.add(self.settings_frame, text='Settings')

        # Content for Settings Tab
        tk.Label(self.settings_frame, text="Under construction...", font=('Arial', 18), fg='gray', bg="#121212").pack(pady=50)


        # --- Transcriber Tab Elements ---
        
        # Record Button
        self.record_button = ttk.Button(self.transcriber_frame, 
                                        text="Record", 
                                        command=self.toggle_recording, 
                                        style='Dark.TButton')
        self.record_button.pack(pady=20, fill=tk.X, padx=20) 

        # Transcribed Text Display (Read-only Text widget)
        self.transcription_display = tk.Text(self.transcriber_frame, 
                                             height=10, 
                                             wrap=tk.WORD, 
                                             font=('Arial', 11),
                                             relief=tk.SUNKEN, 
                                             bg='#1E1E1E', 
                                             fg='white', 
                                             insertbackground='white', 
                                             state=tk.DISABLED 
                                             )
        self.transcription_display.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Initial text insertion for tk.Text
        self.transcription_display.config(state=tk.NORMAL)
        self.transcription_display.insert(tk.END, "Transcribed text will appear here. Select it to copy.")
        self.transcription_display.config(state=tk.DISABLED)


        # Exit Button
        self.exit_button = ttk.Button(master, 
                                      text="Exit", 
                                      command=self.on_closing,
                                      style='Dark.TButton')
        self.exit_button.pack(pady=10)

        # Handle window closing
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the loop checking the queue
        self.master.after(100, self.check_transcription_queue)
        logging.info("GUI initialized successfully.")
    
    def copy_to_clipboard(self, text: str):
        """Copies the given text to the system clipboard."""
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        logging.info("Transcription copied to clipboard.")

    def toggle_recording(self):
        """Toggles the recording state (start/stop)."""
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Starts the audio recording process."""
        self.recording = True
        self.frames = []
        self.start_time = time.time()
        logging.info("Recording started.")
        
        try:
            self.stream = self.p.open(format=FORMAT,
                                     channels=CHANNELS,
                                     rate=RATE,
                                     input=True,
                                     frames_per_buffer=CHUNK)

            # Update button text to show status
            self.record_button.config(text="Stop Recording") 
            
            # Update text display
            self.transcription_display.config(state=tk.NORMAL)
            self.transcription_display.delete('1.0', tk.END)
            self.transcription_display.insert(tk.END, "Recording in progress... (max 30s)")
            self.transcription_display.config(state=tk.DISABLED)
            
            self.read_chunk()
            # Set a timer for automatic stop
            self.record_timer_id = self.master.after(MAX_RECORD_DURATION * 1000, self.auto_stop_recording)

        except Exception as e:
            self.recording = False
            self.record_button.config(text="Record", state=tk.NORMAL) 
            logging.error(f"Microphone stream error on start: {e}")
            messagebox.showerror("Audio Error", f"Could not open microphone stream: {e}\nCheck your microphone connection and permissions.")
            if self.record_timer_id:
                self.master.after_cancel(self.record_timer_id)
                self.record_timer_id = None
            
    def read_chunk(self):
        """Reads one audio chunk and schedules the next call."""
        if self.recording:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                self.master.after(1, self.read_chunk) 
            except IOError as e:
                logging.error(f"Stream read IOError: {e}")
                self.stop_recording()

    def auto_stop_recording(self):
        """Automatically stops recording after MAX_RECORD_DURATION expires."""
        if self.recording:
            logging.info(f"Automatic stop triggered after {MAX_RECORD_DURATION} seconds.")
            self.stop_recording()
            messagebox.showinfo("Recording Finished", f"The recording was stopped automatically after {MAX_RECORD_DURATION} seconds. Starting transcription...")

    def stop_recording(self):
        """Stops the stream, saves the file, and starts the transcription thread."""
        if not self.recording:
            return

        self.recording = False
        
        if self.record_timer_id:
            self.master.after_cancel(self.record_timer_id)
            self.record_timer_id = None

        # Stop and close the stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        logging.info("Audio stream closed.")

        WAVE_OUTPUT_FILENAME, timestamp = output_filename()
        self.current_timestamp = timestamp  # Store for transcription thread

        # Update button status for user feedback
        self.record_button.config(text="Saving...", state=tk.DISABLED) 
        self.master.update_idletasks()

        # Save to WAVE file
        try:
            with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(self.frames))
            logging.info(f"File saved successfully to {WAVE_OUTPUT_FILENAME}")
            
            self.record_button.config(text="Transcribing...")
            
            # Update text in read-only Text widget
            self.transcription_display.config(state=tk.NORMAL)
            self.transcription_display.delete('1.0', tk.END)
            self.transcription_display.insert(tk.END, "Transcription in progress (this may take a while)...")
            self.transcription_display.config(state=tk.DISABLED)
            
            # === START TRANSCRIPTION IN A THREAD ===
            transcription_thread = threading.Thread(
                target=self.run_transcription,
                args=(WAVE_OUTPUT_FILENAME, timestamp),
                daemon=True
            )
            transcription_thread.start()
            logging.info("Transcription thread started.")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save WAVE file: {e}")
            self.record_button.config(text="Record", state=tk.NORMAL) 
            logging.error(f"Error saving wave file: {e}", exc_info=True)

    def run_transcription(self, audio_path, timestamp):
        """
        Method executed in a separate thread. 
        Calls transcription, adds to history, and puts result in the queue.
        """
        logging.info(f"Running transcription for {audio_path} in thread: {threading.get_ident()}")
        transcription = transcribe_audio(audio_path, MODEL_NAME)

        # Only add to history if transcription was successful (no ERROR prefix)
        if transcription and not transcription.startswith("An unexpected error") and not transcription.startswith("ERROR"):
            success = self.history_manager.add_transcription(
                timestamp=timestamp,
                audio_file=audio_path,
                full_text=transcription
            )
            if success:
                logging.info(f"Transcription added to history: {timestamp}")
            else:
                logging.warning(f"Failed to add transcription to history: {timestamp}")
        else:
            logging.warning(f"Transcription failed, not adding to history: {audio_path}")

        self.transcription_queue.put(transcription)

    def check_transcription_queue(self):
        """
        Checks the queue for transcription results.
        Run in the main GUI thread.
        """
        try:
            result = self.transcription_queue.get(block=False)
            
            # Update Transcriber tab (main output)
            self.transcription_display.config(state=tk.NORMAL)
            self.transcription_display.delete('1.0', tk.END)
            self.transcription_display.insert(tk.END, result)
            self.transcription_display.config(state=tk.DISABLED)
            
            # Refresh History tab if transcription was successful
            if not result.startswith("An unexpected error") and not result.startswith("ERROR"):
                self._refresh_history_display()

            if "ERROR" in result:
                logging.warning("Transcription failed with error message.")
                messagebox.showerror("Transcription Failed", "Transcription returned an error. Check logs for details.")
            else:
                # Copy to clipboard upon successful transcription
                self.copy_to_clipboard(result) 
                
            self.record_button.config(text="Record", state=tk.NORMAL) # Return to normal state

        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.check_transcription_queue)

    def _refresh_history_display(self):
        """Refresh the history table display with current data from history manager."""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Load active transcriptions
            history = self.history_manager.load_active_history()

            # Add rows to table (newest first, which is already the order)
            for entry in history:
                timestamp_str = self._format_timestamp(entry.get("timestamp", ""))
                duration_str = f"{entry.get('duration', 0):.1f}s"

                # Truncate preview text to fit UI (approximately 100 chars)
                full_text = entry.get("fullText", "")
                preview = full_text[:100] + "..." if len(full_text) > 100 else full_text

                # Insert row with entry ID as the first element (hidden, but used for deletion)
                item_id = self.history_tree.insert(
                    "",
                    tk.END,
                    iid=entry["id"],  # Use timestamp as unique ID
                    values=(timestamp_str, duration_str, preview)
                )

            logging.info(f"History display refreshed: {len(history)} entries")

        except Exception as e:
            logging.error(f"Error refreshing history display: {e}", exc_info=True)

    def _format_timestamp(self, iso_timestamp: str) -> str:
        """
        Format ISO 8601 timestamp to human-readable format.

        Args:
            iso_timestamp: ISO 8601 timestamp string (e.g., "2025-01-15T14:30:00Z")

        Returns:
            Human-readable format (e.g., "14:30 Jan 15")
        """
        try:
            # Parse ISO format
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            # Format as "HH:MM MMM DD"
            return dt.strftime("%H:%M %b %d").lstrip('0')
        except Exception as e:
            logging.warning(f"Could not format timestamp {iso_timestamp}: {e}")
            return iso_timestamp

    def _on_history_row_double_click(self, event):
        """Handle double-click on history row to show full text."""
        selection = self.history_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        entry = self.history_manager.get_entry_by_id(item_id)

        if entry:
            self._show_full_text_modal(entry)

    def _on_history_delete_key(self, event):
        """Handle Delete key press to delete selected row."""
        self._delete_selected_history()

    def _show_full_text_modal(self, entry: dict):
        """
        Display a modal window showing the full transcription text.

        Args:
            entry: Dictionary containing transcription entry data
        """
        modal = tk.Toplevel(self.master)
        modal.title("Full Transcription")
        modal.geometry("700x500")
        modal.config(bg="#121212")

        # Title with timestamp and duration
        timestamp_str = self._format_timestamp(entry.get("timestamp", ""))
        duration = entry.get("duration", 0)
        title_text = f"Transcription - {timestamp_str} ({duration:.1f}s)"
        tk.Label(modal, text=title_text, font=('Arial', 12, 'bold'), fg='white', bg="#121212").pack(pady=(10, 5))

        # Text display (read-only)
        text_display = tk.Text(
            modal,
            wrap=tk.WORD,
            font=('Arial', 10),
            relief=tk.SUNKEN,
            bg='#1E1E1E',
            fg='white',
            insertbackground='white'
        )
        text_display.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        text_display.insert(tk.END, entry.get("fullText", ""))
        text_display.config(state=tk.DISABLED)

        # Button frame
        button_frame = tk.Frame(modal, bg="#121212")
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        copy_button = ttk.Button(
            button_frame,
            text="Copy to Clipboard",
            command=lambda: self._copy_text_from_modal(entry.get("fullText", "")),
            style='Dark.TButton'
        )
        copy_button.pack(side=tk.LEFT, padx=5)

        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=modal.destroy,
            style='Dark.TButton'
        )
        close_button.pack(side=tk.RIGHT, padx=5)

    def _copy_text_from_modal(self, text: str):
        """Copy text to clipboard and show confirmation."""
        self.copy_to_clipboard(text)
        messagebox.showinfo("Copied", "Text copied to clipboard!")

    def _delete_selected_history(self):
        """Delete the selected history entry (soft-delete with confirmation)."""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transcription to delete.")
            return

        item_id = selection[0]
        entry = self.history_manager.get_entry_by_id(item_id)

        if not entry:
            messagebox.showerror("Error", "Could not find selected entry.")
            return

        # Show confirmation dialog
        timestamp_str = self._format_timestamp(entry.get("timestamp", ""))
        preview = entry.get("fullText", "")[:60] + "..."

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete transcription from {timestamp_str}?\n\n{preview}\n\nThis will delete the audio file permanently."
        )

        if confirm:
            success = self.history_manager.mark_deleted(item_id)
            if success:
                messagebox.showinfo("Deleted", "Transcription deleted successfully.")
                self._refresh_history_display()
            else:
                messagebox.showerror("Error", "Failed to delete transcription. Check logs.")

    def on_closing(self):
        """Handles clean application shutdown."""
        logging.info("Closing application...")
        if self.recording:
            self.stop_recording() 
        
        # Terminate PyAudio
        if self.p:
            self.p.terminate()
        
        self.master.destroy()
        logging.info("Application destroyed.")

# --- Application Startup ---
if __name__ == "__main__":
    logging.info("Whisper model loading might take a moment on first launch...")
    root = tk.Tk()
    app = AudioRecorderApp(root)
    root.mainloop()
