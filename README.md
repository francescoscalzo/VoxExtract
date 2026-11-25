# VoxExtract

> Estrai audio dai tuoi video con stile

VoxExtract è un'applicazione desktop per estrarre tracce audio da file video e convertirle in vari formati audio (MP3, AAC, FLAC, WAV).

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Caratteristiche

- **Interfaccia moderna** - GUI con tema scuro e design Neon/Cyberpunk
- **Supporto multi-formato** - Esporta in MP3, AAC, FLAC o WAV
- **Qualità configurabile** - Scegli tra 128k, 192k, 256k o 320k bitrate
- **Barra di progresso** - Visualizza l'avanzamento in tempo reale
- **Doppia modalità** - Usa la GUI o la linea di comando
- **Multilingua** - Supporto Italiano e Inglese

## Screenshot

```
╔══════════════════════════════════════════════════════════════╗
║                    ✦ VoxExtract ✦                            ║
║            Estrai audio dai tuoi video con stile             ║
╠══════════════════════════════════════════════════════════════╣
║  🎬 File Video:                                              ║
║  ┌────────────────────────────────┐  ┌─────────────┐        ║
║  │ C:/video.mp4                   │  │ 📂 Sfoglia  │        ║
║  └────────────────────────────────┘  └─────────────┘        ║
║                                                              ║
║  💾 Cartella di Output:                                      ║
║  ┌────────────────────────────────┐  ┌─────────────┐        ║
║  │ C:/output                      │  │ 📂 Sfoglia  │        ║
║  └────────────────────────────────┘  └─────────────┘        ║
║                                                              ║
║  ⚙️ Opzioni:  [Qualità: high ▼]  [Formato: MP3 ▼]           ║
║                                                              ║
║              ╔═══════════════════════════╗                   ║
║              ║  ⚡ ESTRAI AUDIO ⚡        ║                   ║
║              ╚═══════════════════════════╝                   ║
╚══════════════════════════════════════════════════════════════╝
```

## Versione Web / App installabile (consigliata)

La cartella [`web/`](web/) contiene VoxExtract come **Progressive Web App**: gira nel browser grazie a [ffmpeg.wasm](https://ffmpegwasm.netlify.app/), senza installare Python né FFmpeg.

- **Nessun blocco** di Windows SmartScreen / Controllo intelligente delle app o di macOS Gatekeeper: non è un eseguibile.
- **Installabile**: in Chrome/Edge clicca *Installa come app* (o l'icona ⊕ nella barra indirizzi); su Safari (Mac) *File → Aggiungi al Dock*. Appare nel menu Start / Dock con la sua icona.
- **Offline** dopo la prima apertura; **privacy**: i file non vengono mai caricati su un server.
- Più file insieme, drag & drop, annullamento, IT/EN.

Pubblicata automaticamente su GitHub Pages a ogni push su `main` che tocca `web/` (workflow `.github/workflows/pages.yml`).

Prova in locale:

```bash
cd web && python3 -m http.server 8000
# apri http://localhost:8000
```

> Limite: i file vengono elaborati in memoria dal browser; video molto lunghi in WAV/FLAC possono superare la memoria disponibile.

## Requisiti (versione desktop Python)

- **Python** 3.10 o superiore
- **FFmpeg** installato e nel PATH di sistema (o nella stessa cartella dell'app)

### Installazione FFmpeg

**Windows:**
```bash
# Con winget
winget install FFmpeg

# Oppure scarica da https://ffmpeg.org/download.html
```

## Installazione

1. Clona il repository:
```bash
git clone https://github.com/tuousername/vox-extract.git
cd vox-extract
```

2. (Opzionale) Crea un ambiente virtuale:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Installa le dipendenze:
```bash
pip install pillow  # Solo per generare l'icona
```

## Utilizzo

### Modalità GUI

```bash
python vox_extract.py
```

### Modalità CLI

```bash
# Estrazione base (output in ./extracted_audio/)
python vox_extract.py video.mp4

# Specifica file di output
python vox_extract.py video.mp4 audio.mp3

# Con qualità e formato personalizzati
python vox_extract.py video.mp4 audio.flac high FLAC
```

**Parametri CLI:**
| Parametro | Descrizione | Valori |
|-----------|-------------|--------|
| `input` | File video di input | Percorso file |
| `output` | File audio di output (opzionale) | Percorso file |
| `quality` | Qualità audio (opzionale) | `low`, `medium`, `high`, `best` |
| `format` | Formato audio (opzionale) | `MP3`, `AAC`, `FLAC`, `WAV` |

## Compilazione Eseguibile

Per creare un eseguibile standalone:

```bash
pip install pyinstaller
pyinstaller VoxExtract.spec
```

L'eseguibile sarà in `dist/VoxExtract.exe`.

> **Nota:** Copia `ffmpeg.exe` nella stessa cartella dell'eseguibile.

## Test

```bash
python -m unittest test_vox_extract -v
```

## Struttura Progetto

```
vox-extract/
├── vox_extract.py      # Applicazione principale
├── test_vox_extract.py # Unit test
├── VoxExtract.spec     # Configurazione PyInstaller
├── create_icon.py      # Generatore icona
├── icon.ico            # Icona applicazione
├── .gitignore
└── README.md
```

## Formati Supportati

### Input (Video)
- MP4, AVI, MKV, MOV, FLV, WMV, WEBM, M4V, MPEG, MPG

### Output (Audio)
| Formato | Codec | Bitrate |
|---------|-------|---------|
| MP3 | libmp3lame | 128k - 320k |
| AAC | aac | 128k - 320k |
| FLAC | flac | Lossless |
| WAV | pcm_s16le | Lossless |

## Licenza

MIT License - vedi [LICENSE](LICENSE) per dettagli.

## Contribuire

1. Fork del progetto
2. Crea un branch (`git checkout -b feature/nuova-funzione`)
3. Commit delle modifiche (`git commit -m 'Aggiunge nuova funzione'`)
4. Push al branch (`git push origin feature/nuova-funzione`)
5. Apri una Pull Request
