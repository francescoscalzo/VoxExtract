# -*- coding: utf-8 -*-
"""
VoxExtract - Estrai audio dai tuoi video con stile
by mascalzonef

Un'applicazione elegante per estrarre tracce audio da file video
e convertirle in vari formati (MP3, AAC, FLAC, WAV).
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import base64
import threading
import logging
import re
from typing import Callable
from dataclasses import dataclass
from enum import Enum

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vox_extract.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# INTERNAZIONALIZZAZIONE (i18n)
# ============================================================================

class Language(Enum):
    """Lingue supportate."""
    IT = "it"
    EN = "en"


TRANSLATIONS: dict[str, dict[str, str]] = {
    "it": {
        "app_title": "VoxExtract",
        "app_subtitle": "Estrai audio dai tuoi video con stile",
        "author": "",
        "video_file": "File Video:",
        "output_folder": "Cartella di Output:",
        "browse": "Sfoglia...",
        "extract_audio": "ESTRAI AUDIO",
        "extracting": "ESTRAZIONE IN CORSO...",
        "extraction_progress": "Estrazione in corso...",
        "powered_by": "Powered by FFmpeg",
        "select_video": "Seleziona file video",
        "select_folder": "Seleziona cartella di output",
        "error": "Errore",
        "success": "Successo",
        "confirm": "Conferma",
        "error_no_video": "Seleziona un file video!",
        "error_file_not_exists": "Il file '{file}' non esiste!",
        "error_no_folder": "Seleziona una cartella di output!",
        "error_video_no_audio": "Il file video non contiene una traccia audio",
        "error_extraction": "Errore durante l'estrazione dell'audio",
        "error_ffmpeg_not_found": "FFmpeg non trovato. Assicurati che sia installato.",
        "confirm_overwrite": "Il file '{file}' esiste già.\nVuoi sovrascriverlo?",
        "confirm_exit_extracting": "Estrazione in corso. Sei sicuro di voler uscire?",
        "success_extracted": "Audio estratto con successo!\n\n{file}",
        "drop_video_here": "Trascina qui un file video",
        "quality": "Qualit\u00e0:",
        "format": "Formato:",
        "quality_low": "Bassa (128 kbps)",
        "quality_medium": "Media (192 kbps)",
        "quality_high": "Alta (256 kbps)",
        "quality_best": "Massima (320 kbps)",
        "progress_percent": "Progresso: {percent}%",
    },
    "en": {
        "app_title": "VoxExtract",
        "app_subtitle": "Extract audio from your videos with style",
        "author": "",
        "video_file": "Video File:",
        "output_folder": "Output Folder:",
        "browse": "Browse...",
        "extract_audio": "EXTRACT AUDIO",
        "extracting": "EXTRACTING...",
        "extraction_progress": "Extraction in progress...",
        "powered_by": "Powered by FFmpeg",
        "select_video": "Select video file",
        "select_folder": "Select output folder",
        "error": "Error",
        "success": "Success",
        "confirm": "Confirm",
        "error_no_video": "Please select a video file!",
        "error_file_not_exists": "File '{file}' does not exist!",
        "error_no_folder": "Please select an output folder!",
        "error_video_no_audio": "The video file does not contain an audio track",
        "error_extraction": "Error during audio extraction",
        "error_ffmpeg_not_found": "FFmpeg not found. Please make sure it is installed.",
        "confirm_overwrite": "File '{file}' already exists.\nDo you want to overwrite it?",
        "confirm_exit_extracting": "Extraction in progress. Are you sure you want to exit?",
        "success_extracted": "Audio extracted successfully!\n\n{file}",
        "drop_video_here": "Drop a video file here",
        "quality": "Quality:",
        "format": "Format:",
        "quality_low": "Low (128 kbps)",
        "quality_medium": "Medium (192 kbps)",
        "quality_high": "High (256 kbps)",
        "quality_best": "Best (320 kbps)",
        "progress_percent": "Progress: {percent}%",
    }
}


def get_text(key: str, lang: Language = Language.IT, **kwargs) -> str:
    """
    Ottiene il testo tradotto per la chiave specificata.

    Args:
        key: Chiave di traduzione
        lang: Lingua desiderata
        **kwargs: Parametri per la formattazione

    Returns:
        Testo tradotto e formattato
    """
    text = TRANSLATIONS.get(lang.value, TRANSLATIONS["it"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

@dataclass
class AudioQuality:
    """Configurazione qualità audio."""
    name: str
    bitrate: str

QUALITY_PRESETS: dict[str, AudioQuality] = {
    "low": AudioQuality("quality_low", "128k"),
    "medium": AudioQuality("quality_medium", "192k"),
    "high": AudioQuality("quality_high", "256k"),
    "best": AudioQuality("quality_best", "320k"),
}

@dataclass
class AudioFormat:
    """Configurazione formato audio."""
    extension: str
    ffmpeg_format: str
    codec: str | None = None

AUDIO_FORMATS: dict[str, AudioFormat] = {
    "MP3": AudioFormat("mp3", "mp3", "libmp3lame"),
    "AAC": AudioFormat("aac", "adts", "aac"),
    "FLAC": AudioFormat("flac", "flac", "flac"),
    "WAV": AudioFormat("wav", "wav", "pcm_s16le"),
}


# ============================================================================
# FUNZIONI CORE
# ============================================================================

def find_ffmpeg() -> str:
    """
    Cerca l'eseguibile FFmpeg nel sistema.

    Cerca nell'ordine:
    1. Stessa directory dell'eseguibile/script
    2. PATH di sistema

    Returns:
        Percorso di FFmpeg

    Raises:
        FileNotFoundError: Se FFmpeg non viene trovato
    """
    # Cerca nella directory dell'eseguibile
    if getattr(sys, 'frozen', False):
        # Eseguibile PyInstaller
        app_dir = os.path.dirname(sys.executable)
    else:
        # Script Python
        app_dir = os.path.dirname(os.path.abspath(__file__))

    # Prova percorsi locali
    local_paths = [
        os.path.join(app_dir, 'ffmpeg.exe'),
        os.path.join(app_dir, 'ffmpeg'),
        os.path.join(app_dir, 'bin', 'ffmpeg.exe'),
        os.path.join(app_dir, 'bin', 'ffmpeg'),
    ]

    for path in local_paths:
        if os.path.isfile(path):
            logger.info(f"FFmpeg trovato: {path}")
            return path

    # Prova nel PATH di sistema
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        logger.info("FFmpeg trovato nel PATH di sistema")
        return 'ffmpeg'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise FileNotFoundError("FFmpeg non trovato")


def get_video_duration(ffmpeg_path: str, input_file: str) -> float | None:
    """
    Ottiene la durata del video in secondi.

    Args:
        ffmpeg_path: Percorso di FFmpeg
        input_file: File video di input

    Returns:
        Durata in secondi o None se non determinabile
    """
    try:
        ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
        if not os.path.isfile(ffprobe_path) and ffprobe_path != 'ffprobe':
            ffprobe_path = 'ffprobe'

        cmd = [
            ffprobe_path, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_file
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Impossibile ottenere durata video: {e}")

    return None


def extract_audio(
    input_file: str,
    output_file: str,
    quality: str = "medium",
    audio_format: str = "MP3",
    progress_callback: Callable[[float], None] | None = None
) -> tuple[bool, str | None]:
    """
    Estrae l'audio da un file video.

    Args:
        input_file: Percorso del file video di input
        output_file: Percorso del file audio di output
        quality: Preset qualità (low, medium, high, best)
        audio_format: Formato output (MP3, AAC, FLAC, WAV)
        progress_callback: Callback per aggiornamenti progresso (0.0-100.0)

    Returns:
        Tupla (successo: bool, messaggio_errore: str | None)
    """
    try:
        # Trova FFmpeg
        try:
            ffmpeg_path = find_ffmpeg()
        except FileNotFoundError:
            return False, get_text("error_ffmpeg_not_found")

        # Normalizza i percorsi
        input_file = os.path.normpath(input_file)
        output_file = os.path.normpath(output_file)

        # Crea cartella di output se non esiste
        output_folder = os.path.dirname(output_file)
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)

        # Ottieni configurazioni
        quality_config = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["medium"])
        format_config = AUDIO_FORMATS.get(audio_format, AUDIO_FORMATS["MP3"])

        # Ottieni durata per progress
        duration = get_video_duration(ffmpeg_path, input_file)

        # Costruisci comando FFmpeg
        command = [
            ffmpeg_path,
            '-i', input_file,
            '-vn',  # No video
            '-acodec', format_config.codec,
            '-ab', quality_config.bitrate,
            '-f', format_config.ffmpeg_format,
            '-y',  # Sovrascrivi
            output_file
        ]

        # Per WAV non serve bitrate
        if audio_format == "WAV":
            command = [
                ffmpeg_path,
                '-i', input_file,
                '-vn',
                '-acodec', format_config.codec,
                '-f', format_config.ffmpeg_format,
                '-y',
                output_file
            ]

        logger.info(f"Esecuzione comando: {' '.join(command)}")

        # Esegui con progress tracking
        process = subprocess.Popen(
            command,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        # Parse output per progress
        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')

        for line in process.stderr:
            if duration and progress_callback:
                match = time_pattern.search(line)
                if match:
                    hours, minutes, seconds, centis = map(int, match.groups())
                    current_time = hours * 3600 + minutes * 60 + seconds + centis / 100
                    progress = min(100.0, (current_time / duration) * 100)
                    progress_callback(progress)

        process.wait()

        # Chiudi i pipe esplicitamente
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

        if process.returncode != 0:
            logger.error("FFmpeg ha restituito un errore")
            return False, get_text("error_extraction")

        if progress_callback:
            progress_callback(100.0)

        logger.info(f"Estrazione completata: {output_file}")
        return True, None

    except Exception as e:
        logger.exception(f"Errore durante l'estrazione: {e}")
        return False, str(e)


# ============================================================================
# ICONA EMBEDDED
# ============================================================================

def get_icon_data() -> str:
    """
    Restituisce i dati dell'icona in formato base64.

    Returns:
        Stringa base64 dell'icona PNG 64x64
    """
    icon_base64 = """
    iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF
    GUlEQVR4nO2bXWgcVRTHz9nd2WR3s5tsNk2aNGlqbGxrq1YRRQsqKCIIPhQfFAQfBEEQX/TB+qCI
    D4qCIj74UPBBfFAQBEUQREHQB0GoCIr4gVqxX7E2TZo0yWazu5Ppmd2ZnczszM7M3t3JJvnDgc3e
    c88993/OPefce2cFYYUVVlhhhf8bBN4KSCaTRdu2bxVFcbssy9sFQdgqCMJGAKjoul7u6+v7TZbl
    XwEgC8sMhmGYpmluEUVxpyiKuyRJ2iJJ0kZN0zboui5qmiYCgKTrelpRlN8VRfldUZRfAOBnABiD
    /yDq6+u/SaVSH4qi+JIgCJul1tBZ2yjL8quKoiRhGSCRSLwjSdJrvKQRs0yWZeV1WRbPwxJGU1PT
    J7Is38sb+EzHviBJ0qei6L7F5QJVVT+SJCnGG3Av5m6RZTEBS2iXoGlaQpblGd7AZjfb0XU9CksA
    0Wj0E1VV8951N1s+rul6DJYAYrHYOVEU74rB9NF+ryiKH8ESgCRJVzRN+583qH5sjaZpl2EJQFLk
    G/BvQJKka7AEoIji+wDwNwAkAeBvALgOAAkAuAoA12AJQFGUqwDwNQBcBoCvAOBLAPgCAL4AgM9h
    CUBRlEsA8CkAXASATwDgYwD4CAA+BIAPYHE7vwsA8D4AvAcA7wLAOwDwNgC8BQAX4D+Aurq6dwHg
    bQB4CwDeBIA3AOB1AHgNAF6FJYDa2tpXAOBlAHgJAF4EgBcA4HkAeA4AngWAZxYb/I8A8AwAPL3Y
    4H8IAPMAsAcA9gLAUwDwJAA8AQBzADALALMAsGex1+BRAHgEAB4GgIcA4EEAOFB2+kMAcAgADgLA
    /rLT7wOA+wBgX9npfQBwLwDsCRj8EACYR0y+BwDuBoBZALgLAO4AgNsB4DYAII+B84sA4BYAuBkA
    bgKAmwDgRgCYhgqQz+dpKvwQANwIADcAwPUAcB0AXAsAU1ABNTU1UwAwCQDXAMA1AHB12SkAmIBV
    q1ZNrF69ehwAxgBgFABGAGAYAK4BgKsBYAgABgGgv+z0IAAMAMAVlZYvAEAfAFxeddUVANAPAH2r
    Vq3qPXTo0Ozdu3dPnzx5cv706dNzp0+ffqz8/vTp009VWk6cODE3Nzf37MmTJ0+cPXv2uZ07dy6e
    Onq7du2aPXXq1NzZs2efP3PmzKnZ2dkXTp48+eKJEydefPHFF188fvz489PT089MT08/e+zYsefm
    5+dfmpube2l+fv7lY8eOvTo7O/v68ePH3zh69Ojc0aNHT8zMzLx18uTJt48cOfLO/Pz8O9PT0+/O
    zMy8d/jw4fcPHTr0wczMzAeHDh364ODBgx8ePHjww/379394YP+Bhf0HDhw6ePDQRwcOHPjw4MGD
    H+3fv//j/fv3f7xv374FfW7v3r2f7Nu379M9e/Z8tmfPns/37Nnz+Z49ez7fu3fvF3v27Pli9+7d
    X+7evfvL3bt3f7V79+6vdu3a9fXu3bu/2rlz5ze7du36ZmZm5tvp6elv9+zZ8+2ePXu+3bVr17d7
    9+79bvfu3d/t3Lnz+507d36/Y8eO73fs2PH99u3bF/Sbdu7c+cOOHTt+2L59+4/btm37cevWrT9u
    3br1p61bt/60devWn7Zs2fLzli1bft6yZcvPW7Zs+WXz5s2/bN269ddNmzb9unnz5t82bdq0sH79
    +oX169cvbNiw4dfVq1f/tnr16oW1a9curFmzZmH16tW/rl27dmHNmjUL69ate3D9+vUPrl279sF1
    69Y9uHbt2ofWrFnz8Jo1ax5as2bNwpo1axbWrVv30Nq1ax9at27dQ+vXr394/fr1D2/YsOHhDRs2
    PLxhw4aFdevWLaxbt25h/fr1C+vXr1/YsGHDwsaNG3/fuHHj7xs3bvx948aNC2vXrl1Yv379wobS
    LwsrLAf8A7H5C9JVMwQaAAAAAElFTkSuQmCC
    """
    return icon_base64.strip()


# ============================================================================
# GUI
# ============================================================================

class VoxExtractGUI:
    """
    Interfaccia grafica per VoxExtract.

    Fornisce un'interfaccia utente moderna con supporto per:
    - Selezione file video
    - Scelta qualità e formato audio
    - Barra di progresso con percentuale
    - Tema scuro moderno
    """

    def __init__(self, root: tk.Tk, lang: Language = Language.IT):
        """
        Inizializza la GUI.

        Args:
            root: Finestra Tk principale
            lang: Lingua dell'interfaccia
        """
        self.root = root
        self.lang = lang
        self.root.title(get_text('app_title', lang))
        self.root.geometry("700x720")
        self.root.resizable(False, False)

        # Palette colori moderna (Cyberpunk/Neon)
        self.colors = {
            'bg_dark': '#0f0f1a',
            'bg_card': '#1a1a2e',
            'bg_input': '#252542',
            'accent_purple': '#7c3aed',
            'accent_purple_hover': '#8b5cf6',
            'accent_cyan': '#06b6d4',
            'accent_cyan_hover': '#22d3ee',
            'accent_pink': '#ec4899',
            'accent_pink_hover': '#f472b6',
            'success': '#10b981',
            'success_hover': '#34d399',
            'text_primary': '#f8fafc',
            'text_secondary': '#94a3b8',
            'text_muted': '#64748b',
            'border': '#3b3b5c',
            'glow': '#7c3aed',
        }

        self.root.configure(bg=self.colors['bg_dark'])

        # Imposta icona
        self._setup_icon()

        # Variabili
        self.input_video = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.selected_quality = tk.StringVar(value="high")
        self.selected_format = tk.StringVar(value="MP3")
        self.is_extracting = False
        self.current_progress = 0.0

        # Configura stili ttk
        self._setup_styles()

        # Gestione chiusura finestra
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Crea widgets
        self._create_widgets()

    def _setup_styles(self) -> None:
        """Configura gli stili ttk personalizzati."""
        style = ttk.Style()
        style.theme_use('clam')

        # Stile Combobox
        style.configure(
            'Custom.TCombobox',
            fieldbackground=self.colors['bg_input'],
            background=self.colors['bg_input'],
            foreground=self.colors['text_primary'],
            arrowcolor=self.colors['accent_cyan'],
            borderwidth=2,
            relief='flat',
            padding=10
        )
        style.map('Custom.TCombobox',
            fieldbackground=[('readonly', self.colors['bg_input'])],
            selectbackground=[('readonly', self.colors['accent_purple'])],
            selectforeground=[('readonly', self.colors['text_primary'])]
        )

        # Stile Progress bar con gradiente
        style.configure(
            'Neon.Horizontal.TProgressbar',
            troughcolor=self.colors['bg_input'],
            background=self.colors['accent_cyan'],
            lightcolor=self.colors['accent_purple'],
            darkcolor=self.colors['accent_pink'],
            borderwidth=0,
            thickness=25
        )

    def _setup_icon(self) -> None:
        """Configura l'icona della finestra."""
        try:
            icon_data = get_icon_data()
            icon_bytes = base64.b64decode(icon_data)
            icon_image = tk.PhotoImage(data=icon_bytes)
            self.root.iconphoto(True, icon_image)
        except Exception as e:
            logger.warning(f"Impossibile caricare icona: {e}")

    def _on_closing(self) -> None:
        """Gestisce la chiusura della finestra."""
        if self.is_extracting:
            if messagebox.askyesno(
                get_text("confirm", self.lang),
                get_text("confirm_exit_extracting", self.lang)
            ):
                self.root.destroy()
        else:
            self.root.destroy()

    def _create_card(self, parent: tk.Frame, **kwargs) -> tk.Frame:
        """Crea un frame card con bordo e sfondo."""
        card = tk.Frame(
            parent,
            bg=self.colors['bg_card'],
            highlightbackground=self.colors['border'],
            highlightthickness=1,
            **kwargs
        )
        return card

    def _create_neon_button(
        self,
        parent: tk.Frame,
        text: str,
        command,
        color_key: str = 'accent_purple',
        size: str = 'normal'
    ) -> tk.Button:
        """Crea un pulsante con effetto neon."""
        font_size = 12 if size == 'normal' else 14
        pad_x = 25 if size == 'normal' else 50
        pad_y = 10 if size == 'normal' else 18

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", font_size, "bold"),
            bg=self.colors[color_key],
            fg=self.colors['text_primary'],
            activebackground=self.colors[f'{color_key}_hover'],
            activeforeground=self.colors['text_primary'],
            relief=tk.FLAT,
            bd=0,
            padx=pad_x,
            pady=pad_y,
            cursor="hand2"
        )

        # Effetti hover
        hover_color = self.colors[f'{color_key}_hover']
        normal_color = self.colors[color_key]

        def on_enter(e):
            if not self.is_extracting:
                btn.config(bg=hover_color)

        def on_leave(e):
            if not self.is_extracting:
                btn.config(bg=normal_color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def _create_styled_entry(self, parent: tk.Frame, textvariable: tk.StringVar) -> tk.Entry:
        """Crea un campo di input stilizzato."""
        # Frame contenitore con bordo
        container = tk.Frame(
            parent,
            bg=self.colors['border'],
            padx=2,
            pady=2
        )

        entry = tk.Entry(
            container,
            textvariable=textvariable,
            font=("Consolas", 11),
            bg=self.colors['bg_input'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['accent_cyan'],
            relief=tk.FLAT,
            bd=10,
            highlightthickness=0
        )
        entry.pack(fill=tk.X, expand=True)

        return container, entry

    def _create_widgets(self) -> None:
        """Crea tutti i widget dell'interfaccia."""
        # Header
        self._create_header()

        # Container principale con padding
        main_container = tk.Frame(self.root, bg=self.colors['bg_dark'], padx=30, pady=5)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Card principale
        main_card = self._create_card(main_container, padx=25, pady=20)
        main_card.pack(fill=tk.BOTH, expand=True)

        # Sezione file video
        self._create_video_section(main_card)

        # Separatore
        self._create_separator(main_card)

        # Sezione output
        self._create_output_section(main_card)

        # Separatore
        self._create_separator(main_card)

        # Sezione opzioni
        self._create_options_section(main_card)

        # Pulsante estrazione
        self._create_extract_button(main_card)

        # Sezione progresso
        self._create_progress_section(main_card)

        # Footer
        self._create_footer()

    def _create_separator(self, parent: tk.Frame) -> None:
        """Crea un separatore orizzontale stilizzato."""
        sep_frame = tk.Frame(parent, bg=self.colors['bg_card'], height=20)
        sep_frame.pack(fill=tk.X)

        # Linea gradiente simulata
        canvas = tk.Canvas(
            sep_frame,
            height=2,
            bg=self.colors['bg_card'],
            highlightthickness=0
        )
        canvas.pack(fill=tk.X, pady=8)

        # Disegna linea sfumata
        def draw_gradient(event=None):
            canvas.delete("all")
            width = canvas.winfo_width()
            if width > 1:
                for i in range(width):
                    # Sfumatura dal centro verso i bordi
                    center = width / 2
                    dist = abs(i - center) / center
                    alpha = 1 - dist
                    # Colore interpolato
                    r = int(124 * alpha + 15 * (1-alpha))
                    g = int(58 * alpha + 15 * (1-alpha))
                    b = int(237 * alpha + 26 * (1-alpha))
                    color = f'#{r:02x}{g:02x}{b:02x}'
                    canvas.create_line(i, 0, i, 2, fill=color)

        canvas.bind('<Configure>', draw_gradient)

    def _create_header(self) -> None:
        """Crea l'header con titolo animato."""
        header_frame = tk.Frame(self.root, bg=self.colors['bg_dark'], pady=25)
        header_frame.pack(fill=tk.X)

        # Icona e titolo
        title_text = f"✦ {get_text('app_title', self.lang)} ✦"
        title_label = tk.Label(
            header_frame,
            text=title_text,
            font=("Segoe UI", 32, "bold"),
            bg=self.colors['bg_dark'],
            fg=self.colors['accent_purple']
        )
        title_label.pack()

        # Sottotitolo con colore accent
        subtitle_label = tk.Label(
            header_frame,
            text=get_text("app_subtitle", self.lang),
            font=("Segoe UI", 12),
            bg=self.colors['bg_dark'],
            fg=self.colors['text_secondary']
        )
        subtitle_label.pack(pady=(5, 0))

    def _create_video_section(self, parent: tk.Frame) -> None:
        """Crea la sezione per la selezione del file video."""
        section = tk.Frame(parent, bg=self.colors['bg_card'])
        section.pack(fill=tk.X, pady=(0, 5))

        # Label con icona
        label_frame = tk.Frame(section, bg=self.colors['bg_card'])
        label_frame.pack(fill=tk.X, pady=(0, 8))

        icon_label = tk.Label(
            label_frame,
            text="🎬",
            font=("Segoe UI", 14),
            bg=self.colors['bg_card'],
            fg=self.colors['accent_pink']
        )
        icon_label.pack(side=tk.LEFT)

        text_label = tk.Label(
            label_frame,
            text=get_text('video_file', self.lang),
            font=("Segoe UI", 12, "bold"),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        )
        text_label.pack(side=tk.LEFT, padx=(5, 0))

        # Frame input
        input_frame = tk.Frame(section, bg=self.colors['bg_card'])
        input_frame.pack(fill=tk.X)

        # Entry stilizzato
        entry_container, self.video_entry = self._create_styled_entry(input_frame, self.input_video)
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))

        # Pulsante
        browse_btn = self._create_neon_button(
            input_frame,
            f"📂 {get_text('browse', self.lang)}",
            self._select_video,
            'accent_cyan'
        )
        browse_btn.pack(side=tk.RIGHT)

    def _create_output_section(self, parent: tk.Frame) -> None:
        """Crea la sezione per la selezione della cartella output."""
        section = tk.Frame(parent, bg=self.colors['bg_card'])
        section.pack(fill=tk.X, pady=(5, 5))

        # Label con icona
        label_frame = tk.Frame(section, bg=self.colors['bg_card'])
        label_frame.pack(fill=tk.X, pady=(0, 8))

        icon_label = tk.Label(
            label_frame,
            text="💾",
            font=("Segoe UI", 14),
            bg=self.colors['bg_card'],
            fg=self.colors['accent_cyan']
        )
        icon_label.pack(side=tk.LEFT)

        text_label = tk.Label(
            label_frame,
            text=get_text('output_folder', self.lang),
            font=("Segoe UI", 12, "bold"),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        )
        text_label.pack(side=tk.LEFT, padx=(5, 0))

        # Frame input
        input_frame = tk.Frame(section, bg=self.colors['bg_card'])
        input_frame.pack(fill=tk.X)

        # Entry stilizzato
        entry_container, self.folder_entry = self._create_styled_entry(input_frame, self.output_folder)
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))

        # Pulsante
        browse_btn = self._create_neon_button(
            input_frame,
            f"📂 {get_text('browse', self.lang)}",
            self._select_folder,
            'accent_cyan'
        )
        browse_btn.pack(side=tk.RIGHT)

    def _create_options_section(self, parent: tk.Frame) -> None:
        """Crea la sezione delle opzioni (qualità e formato)."""
        section = tk.Frame(parent, bg=self.colors['bg_card'])
        section.pack(fill=tk.X, pady=(5, 15))

        # Titolo sezione
        title_frame = tk.Frame(section, bg=self.colors['bg_card'])
        title_frame.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            title_frame,
            text="⚙️",
            font=("Segoe UI", 14),
            bg=self.colors['bg_card'],
            fg=self.colors['accent_purple']
        ).pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text="Opzioni di Esportazione",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary']
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Container opzioni
        options_container = tk.Frame(section, bg=self.colors['bg_card'])
        options_container.pack(fill=tk.X)

        # Card Qualità
        quality_card = tk.Frame(
            options_container,
            bg=self.colors['bg_input'],
            padx=15,
            pady=12
        )
        quality_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        tk.Label(
            quality_card,
            text="🎚️ " + get_text('quality', self.lang),
            font=("Segoe UI", 10, "bold"),
            bg=self.colors['bg_input'],
            fg=self.colors['accent_pink']
        ).pack(anchor='w', pady=(0, 5))

        self.quality_combo = ttk.Combobox(
            quality_card,
            textvariable=self.selected_quality,
            values=["low", "medium", "high", "best"],
            state="readonly",
            font=("Segoe UI", 10),
            style='Custom.TCombobox'
        )
        self.quality_combo.pack(fill=tk.X)
        self.quality_combo.set("high")

        # Card Formato
        format_card = tk.Frame(
            options_container,
            bg=self.colors['bg_input'],
            padx=15,
            pady=12
        )
        format_card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        tk.Label(
            format_card,
            text="🎵 " + get_text('format', self.lang),
            font=("Segoe UI", 10, "bold"),
            bg=self.colors['bg_input'],
            fg=self.colors['accent_cyan']
        ).pack(anchor='w', pady=(0, 5))

        self.format_combo = ttk.Combobox(
            format_card,
            textvariable=self.selected_format,
            values=list(AUDIO_FORMATS.keys()),
            state="readonly",
            font=("Segoe UI", 10),
            style='Custom.TCombobox'
        )
        self.format_combo.pack(fill=tk.X)
        self.format_combo.set("MP3")

    def _create_extract_button(self, parent: tk.Frame) -> None:
        """Crea il pulsante di estrazione principale."""
        btn_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        btn_frame.pack(fill=tk.X, pady=(10, 5))

        self.execute_button = self._create_neon_button(
            btn_frame,
            f"⚡ {get_text('extract_audio', self.lang)} ⚡",
            self._execute_extraction,
            'success',
            'large'
        )
        self.execute_button.pack(pady=10)

    def _create_progress_section(self, parent: tk.Frame) -> None:
        """Crea la sezione della barra di progresso."""
        self.progress_frame = tk.Frame(parent, bg=self.colors['bg_card'])

        # Label stato
        self.progress_label = tk.Label(
            self.progress_frame,
            text=get_text("extraction_progress", self.lang),
            font=("Segoe UI", 11),
            bg=self.colors['bg_card'],
            fg=self.colors['accent_cyan']
        )
        self.progress_label.pack(pady=(5, 10))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            style='Neon.Horizontal.TProgressbar',
            mode='determinate',
            length=500,
            maximum=100
        )
        self.progress_bar.pack()

        # Percentuale
        self.progress_percent_label = tk.Label(
            self.progress_frame,
            text="0%",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors['bg_card'],
            fg=self.colors['success']
        )
        self.progress_percent_label.pack(pady=(10, 5))

    def _create_footer(self) -> None:
        """Crea il footer."""
        footer_frame = tk.Frame(self.root, bg=self.colors['bg_dark'], pady=8)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        footer_label = tk.Label(
            footer_frame,
            text=f"⚡ {get_text('powered_by', self.lang)} │ FFmpeg",
            font=("Segoe UI", 9),
            bg=self.colors['bg_dark'],
            fg=self.colors['text_muted']
        )
        footer_label.pack()

    def _bind_hover(self, button: tk.Button, normal_color: str, hover_color: str) -> None:
        """Aggiunge effetto hover a un pulsante."""
        button.bind("<Enter>", lambda e: button.config(bg=hover_color) if not self.is_extracting else None)
        button.bind("<Leave>", lambda e: button.config(bg=normal_color) if not self.is_extracting else None)

    def _select_video(self) -> None:
        """Apre il dialog per selezionare un file video."""
        filename = filedialog.askopenfilename(
            title=get_text("select_video", self.lang),
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm *.m4v *.mpeg *.mpg"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_video.set(filename)

    def _select_folder(self) -> None:
        """Apre il dialog per selezionare la cartella di output."""
        folder = filedialog.askdirectory(title=get_text("select_folder", self.lang))
        if folder:
            self.output_folder.set(folder)

    def _execute_extraction(self) -> None:
        """Valida gli input e avvia l'estrazione."""
        if self.is_extracting:
            return

        input_file = self.input_video.get().strip()
        output_folder = self.output_folder.get().strip()

        # Validazione
        if not input_file:
            messagebox.showerror(
                get_text("error", self.lang),
                get_text("error_no_video", self.lang)
            )
            return

        if not os.path.isfile(input_file):
            messagebox.showerror(
                get_text("error", self.lang),
                get_text("error_file_not_exists", self.lang, file=input_file)
            )
            return

        if not output_folder:
            messagebox.showerror(
                get_text("error", self.lang),
                get_text("error_no_folder", self.lang)
            )
            return

        # Costruisci percorso output
        input_name = os.path.splitext(os.path.basename(input_file))[0]
        audio_format = self.selected_format.get()
        extension = AUDIO_FORMATS[audio_format].extension
        output_file = os.path.join(output_folder, f"{input_name}.{extension}")

        # Conferma sovrascrittura
        if os.path.exists(output_file):
            if not messagebox.askyesno(
                get_text("confirm", self.lang),
                get_text("confirm_overwrite", self.lang, file=os.path.basename(output_file))
            ):
                return

        # Avvia estrazione
        self._start_extraction(input_file, output_file)

    def _start_extraction(self, input_file: str, output_file: str) -> None:
        """Avvia l'estrazione in un thread separato."""
        self.is_extracting = True

        # Aggiorna UI
        self.execute_button.config(
            state=tk.DISABLED,
            bg="#666666",
            cursor="arrow",
            text=f"⏳ {get_text('extracting', self.lang)}"
        )

        # Reset e mostra progress
        self.progress_bar['value'] = 0
        self.progress_percent_label.config(text="0%")
        self.progress_frame.pack(pady=10)

        # Avvia thread
        thread = threading.Thread(
            target=self._run_extraction,
            args=(input_file, output_file)
        )
        thread.daemon = True
        thread.start()

    def _run_extraction(self, input_file: str, output_file: str) -> None:
        """Esegue l'estrazione (in thread separato)."""
        def progress_callback(progress: float) -> None:
            self.root.after(0, self._update_progress, progress)

        success, error_msg = extract_audio(
            input_file,
            output_file,
            quality=self.selected_quality.get(),
            audio_format=self.selected_format.get(),
            progress_callback=progress_callback
        )

        # Torna al thread principale
        self.root.after(0, self._extraction_complete, success, output_file, error_msg)

    def _update_progress(self, progress: float) -> None:
        """Aggiorna la barra di progresso."""
        self.current_progress = progress
        self.progress_bar['value'] = progress
        self.progress_percent_label.config(text=f"{int(progress)}%")

    def _extraction_complete(self, success: bool, output_file: str, error_msg: str | None) -> None:
        """Gestisce il completamento dell'estrazione."""
        # Nascondi progress
        self.progress_frame.pack_forget()

        # Riabilita UI
        self.is_extracting = False
        self.execute_button.config(
            state=tk.NORMAL,
            bg=self.success_color,
            cursor="hand2",
            text=f"🚀 {get_text('extract_audio', self.lang)}"
        )

        # Mostra risultato
        if success:
            messagebox.showinfo(
                f"✅ {get_text('success', self.lang)}",
                get_text("success_extracted", self.lang, file=output_file)
            )
        else:
            messagebox.showerror(
                f"❌ {get_text('error', self.lang)}",
                error_msg or get_text("error_extraction", self.lang)
            )


# ============================================================================
# CLI
# ============================================================================

def run_cli(args: list[str]) -> int:
    """
    Esegue VoxExtract in modalità command line.

    Args:
        args: Argomenti da riga di comando [input_video, output_file?, quality?, format?]

    Returns:
        Exit code (0 = successo, 1 = errore)
    """
    if len(args) < 1:
        print("Uso: vox_extract.py <video_input> [output_file] [quality] [format]")
        print("  quality: low, medium, high, best (default: medium)")
        print("  format: MP3, AAC, FLAC, WAV (default: MP3)")
        return 1

    input_video = args[0]
    print(f"[VIDEO] Input: {input_video}")

    if not os.path.isfile(input_video):
        print(f"[ERRORE] Il file '{input_video}' non esiste.")
        return 1

    # Parse argomenti opzionali
    quality = "medium"
    audio_format = "MP3"

    if len(args) >= 2:
        output_file = args[1]
    else:
        output_folder = "extracted_audio"
        os.makedirs(output_folder, exist_ok=True)
        extension = AUDIO_FORMATS[audio_format].extension
        output_file = os.path.join(
            output_folder,
            os.path.splitext(os.path.basename(input_video))[0] + f".{extension}"
        )

    if len(args) >= 3 and args[2] in QUALITY_PRESETS:
        quality = args[2]

    if len(args) >= 4 and args[3] in AUDIO_FORMATS:
        audio_format = args[3]

    print(f"[AUDIO] Output: {output_file}")
    print(f"[QUALITA] {quality}")
    print(f"[FORMATO] {audio_format}")
    print("[...] Estrazione in corso...")

    def progress_callback(progress: float) -> None:
        print(f"\r[...] Progresso: {int(progress)}%", end="", flush=True)

    success, error_msg = extract_audio(
        input_video,
        output_file,
        quality=quality,
        audio_format=audio_format,
        progress_callback=progress_callback
    )

    print()  # Nuova riga dopo progress

    if success:
        print(f"[OK] Audio estratto con successo: {output_file}")
        return 0
    else:
        print(f"[ERRORE] {error_msg}")
        return 1


def run_gui() -> None:
    """Avvia l'interfaccia grafica."""
    root = tk.Tk()

    VoxExtractGUI(root)
    root.mainloop()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Modalità GUI
        run_gui()
    else:
        # Modalità CLI
        exit_code = run_cli(sys.argv[1:])
        sys.exit(exit_code)
