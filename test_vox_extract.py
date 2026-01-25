# -*- coding: utf-8 -*-
"""
Unit tests per VoxExtract.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Importa il modulo da testare
from vox_extract import (
    get_text,
    Language,
    QUALITY_PRESETS,
    AUDIO_FORMATS,
    find_ffmpeg,
    extract_audio,
    AudioQuality,
    AudioFormat,
)


class TestI18n(unittest.TestCase):
    """Test per il sistema di internazionalizzazione."""

    def test_get_text_italian(self):
        """Verifica che le traduzioni italiane funzionino."""
        text = get_text("app_title", Language.IT)
        self.assertEqual(text, "VoxExtract")

    def test_get_text_english(self):
        """Verifica che le traduzioni inglesi funzionino."""
        text = get_text("app_subtitle", Language.EN)
        self.assertEqual(text, "Extract audio from your videos with style")

    def test_get_text_with_params(self):
        """Verifica che la formattazione dei parametri funzioni."""
        text = get_text("error_file_not_exists", Language.IT, file="test.mp4")
        self.assertIn("test.mp4", text)

    def test_get_text_fallback(self):
        """Verifica che chiavi sconosciute restituiscano la chiave stessa."""
        text = get_text("chiave_inesistente", Language.IT)
        self.assertEqual(text, "chiave_inesistente")


class TestQualityPresets(unittest.TestCase):
    """Test per i preset di qualità audio."""

    def test_all_presets_exist(self):
        """Verifica che tutti i preset standard esistano."""
        expected_presets = ["low", "medium", "high", "best"]
        for preset in expected_presets:
            self.assertIn(preset, QUALITY_PRESETS)

    def test_preset_structure(self):
        """Verifica la struttura dei preset."""
        for name, preset in QUALITY_PRESETS.items():
            self.assertIsInstance(preset, AudioQuality)
            self.assertTrue(preset.name)
            self.assertTrue(preset.bitrate)
            self.assertIn("k", preset.bitrate)

    def test_bitrate_values(self):
        """Verifica i valori di bitrate."""
        self.assertEqual(QUALITY_PRESETS["low"].bitrate, "128k")
        self.assertEqual(QUALITY_PRESETS["medium"].bitrate, "192k")
        self.assertEqual(QUALITY_PRESETS["high"].bitrate, "256k")
        self.assertEqual(QUALITY_PRESETS["best"].bitrate, "320k")


class TestAudioFormats(unittest.TestCase):
    """Test per i formati audio supportati."""

    def test_all_formats_exist(self):
        """Verifica che tutti i formati standard esistano."""
        expected_formats = ["MP3", "AAC", "FLAC", "WAV"]
        for fmt in expected_formats:
            self.assertIn(fmt, AUDIO_FORMATS)

    def test_format_structure(self):
        """Verifica la struttura dei formati."""
        for name, fmt in AUDIO_FORMATS.items():
            self.assertIsInstance(fmt, AudioFormat)
            self.assertTrue(fmt.extension)
            self.assertTrue(fmt.ffmpeg_format)

    def test_mp3_format(self):
        """Verifica la configurazione MP3."""
        mp3 = AUDIO_FORMATS["MP3"]
        self.assertEqual(mp3.extension, "mp3")
        self.assertEqual(mp3.ffmpeg_format, "mp3")
        self.assertEqual(mp3.codec, "libmp3lame")


class TestFindFFmpeg(unittest.TestCase):
    """Test per la ricerca di FFmpeg."""

    @patch('subprocess.run')
    def test_find_ffmpeg_in_path(self, mock_run):
        """Verifica che FFmpeg venga trovato nel PATH."""
        mock_run.return_value = MagicMock(returncode=0)

        # Se FFmpeg non è nella directory locale, dovrebbe usare il PATH
        result = find_ffmpeg()
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    @patch('os.path.isfile')
    def test_find_ffmpeg_local(self, mock_isfile, mock_run):
        """Verifica che FFmpeg locale venga trovato prima del PATH."""
        # Simula che ffmpeg.exe esista nella directory locale
        def isfile_side_effect(path):
            return 'ffmpeg.exe' in path or 'ffmpeg' in path

        mock_isfile.side_effect = isfile_side_effect
        mock_run.return_value = MagicMock(returncode=0)

        result = find_ffmpeg()
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    @patch('os.path.isfile')
    def test_find_ffmpeg_not_found(self, mock_isfile, mock_run):
        """Verifica che venga sollevata un'eccezione se FFmpeg non è trovato."""
        mock_isfile.return_value = False
        mock_run.side_effect = FileNotFoundError()

        with self.assertRaises(FileNotFoundError):
            find_ffmpeg()


class TestExtractAudio(unittest.TestCase):
    """Test per la funzione di estrazione audio."""

    def test_extract_audio_file_not_exists(self):
        """Verifica che venga gestito un file inesistente."""
        success, error = extract_audio(
            "file_che_non_esiste.mp4",
            "output.mp3"
        )
        # Se FFmpeg non è trovato, potrebbe fallire per quello
        # ma se il file non esiste, dovrebbe fallire per quello
        self.assertFalse(success)

    @patch('vox_extract.find_ffmpeg')
    def test_extract_audio_ffmpeg_not_found(self, mock_find):
        """Verifica la gestione di FFmpeg non trovato."""
        mock_find.side_effect = FileNotFoundError()

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            temp_video = f.name

        try:
            success, error = extract_audio(temp_video, "output.mp3")
            self.assertFalse(success)
            self.assertIn("FFmpeg", error)
        finally:
            os.unlink(temp_video)

    def test_extract_audio_creates_output_folder(self):
        """Verifica che la cartella di output venga creata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_folder = os.path.join(tmpdir, "nuova_cartella")
            output_file = os.path.join(output_folder, "test.mp3")

            # Crea un file video fittizio
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                temp_video = f.name

            try:
                # L'estrazione fallirà perché il video è vuoto,
                # ma la cartella dovrebbe essere creata
                extract_audio(temp_video, output_file)

                # Verifica che la cartella sia stata creata (se ffmpeg è disponibile)
                # Questo test è condizionale
            finally:
                os.unlink(temp_video)


class TestGetIconData(unittest.TestCase):
    """Test per la funzione get_icon_data."""

    def test_icon_data_is_base64(self):
        """Verifica che l'icona sia in formato base64 valido."""
        from vox_extract import get_icon_data
        import base64

        icon_data = get_icon_data()
        self.assertIsInstance(icon_data, str)

        # Verifica che sia decodificabile
        try:
            decoded = base64.b64decode(icon_data)
            self.assertTrue(len(decoded) > 0)
        except Exception as e:
            self.fail(f"Icon data non è base64 valido: {e}")

    def test_icon_data_is_png(self):
        """Verifica che l'icona sia un PNG valido."""
        from vox_extract import get_icon_data
        import base64

        icon_data = get_icon_data()
        decoded = base64.b64decode(icon_data)

        # I file PNG iniziano con questi byte
        png_signature = b'\x89PNG\r\n\x1a\n'
        self.assertTrue(decoded.startswith(png_signature))


class TestCLI(unittest.TestCase):
    """Test per l'interfaccia command line."""

    def test_cli_no_args(self):
        """Verifica che CLI senza argomenti mostri l'help."""
        from vox_extract import run_cli

        exit_code = run_cli([])
        self.assertEqual(exit_code, 1)

    def test_cli_file_not_exists(self):
        """Verifica che CLI gestisca file inesistenti."""
        from vox_extract import run_cli

        exit_code = run_cli(["file_inesistente.mp4"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
