"""
config.py — Application-wide configuration for AI Language Translator.

Centralises language definitions, app metadata, logging setup,
and UI constants so every module can import from one place.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Dict


# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------

APP_NAME = "AI Language Translator"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Translate text between 50+ languages instantly, "
    "with automatic language detection and text-to-speech output."
)
APP_ICON = "🌐"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger and return the application logger.

    Args:
        level: Logging level (default: INFO).

    Returns:
        Configured Logger instance.
    """
    logging.basicConfig(
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
        level=level,
    )
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# Language catalogue
# ---------------------------------------------------------------------------

# Maps human-readable language name → ISO 639-1 code used by deep-translator.
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "Auto-Detect": "auto",
    "Afrikaans": "af",
    "Albanian": "sq",
    "Arabic": "ar",
    "Bengali": "bn",
    "Bosnian": "bs",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Hebrew": "iw",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Kannada": "kn",
    "Korean": "ko",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Malay": "ms",
    "Maltese": "mt",
    "Marathi": "mr",
    "Norwegian": "no",
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Punjabi": "pa",
    "Romanian": "ro",
    "Russian": "ru",
    "Serbian": "sr",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tamil": "ta",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Welsh": "cy",
}

# Languages that support text-to-speech via gTTS.
# Reference: https://gtts.readthedocs.io/en/latest/module.html#languages-gtts-lang
TTS_SUPPORTED_LANGUAGES: Dict[str, str] = {
    "af": "af",
    "ar": "ar",
    "bg": "bg",
    "bn": "bn",
    "bs": "bs",
    "ca": "ca",
    "cs": "cs",
    "cy": "cy",
    "da": "da",
    "de": "de",
    "el": "el",
    "en": "en",
    "eo": "eo",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "gu": "gu",
    "hi": "hi",
    "hr": "hr",
    "hu": "hu",
    "hy": "hy",
    "id": "id",
    "is": "is",
    "it": "it",
    "ja": "ja",
    "ka": "ka",
    "km": "km",
    "ko": "ko",
    "la": "la",
    "lv": "lv",
    "mk": "mk",
    "ml": "ml",
    "mr": "mr",
    "my": "my",
    "ne": "ne",
    "nl": "nl",
    "no": "no",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "ru": "ru",
    "si": "si",
    "sk": "sk",
    "sq": "sq",
    "sr": "sr",
    "su": "su",
    "sv": "sv",
    "sw": "sw",
    "ta": "ta",
    "te": "te",
    "th": "th",
    "tl": "tl",
    "tr": "tr",
    "uk": "uk",
    "ur": "ur",
    "vi": "vi",
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
}

# Convenience list of language names (without "Auto-Detect") for target dropdowns.
TARGET_LANGUAGE_NAMES: list[str] = [
    lang for lang in SUPPORTED_LANGUAGES if lang != "Auto-Detect"
]

# Source language names (includes "Auto-Detect").
SOURCE_LANGUAGE_NAMES: list[str] = list(SUPPORTED_LANGUAGES.keys())

# ---------------------------------------------------------------------------
# UI / UX constants
# ---------------------------------------------------------------------------

MAX_INPUT_CHARS: int = 5_000          # Hard cap on input text length
HISTORY_MAX_ENTRIES: int = 20         # Max rows kept in session history
TRANSLATION_TIMEOUT_SECONDS: int = 15 # Timeout for network requests
DEFAULT_SOURCE_LANGUAGE: str = "Auto-Detect"
DEFAULT_TARGET_LANGUAGE: str = "Spanish"

# File upload limits
MAX_FILE_SIZE_BYTES: int = 500_000    # 500 KB max upload size
ALLOWED_UPLOAD_EXTENSIONS: tuple[str, ...] = (".txt", ".docx")


# ---------------------------------------------------------------------------
# DataClass: TranslationRecord
# ---------------------------------------------------------------------------

@dataclass
class TranslationRecord:
    """Immutable record stored in session translation history.

    Attributes:
        source_lang:     Human-readable source language name.
        target_lang:     Human-readable target language name.
        original_text:   The text that was submitted for translation.
        translated_text: The result returned by the translation engine.
        timestamp:       ISO-format datetime string (set at creation time).
        detected_lang:   The ISO code detected by the engine (if auto-detect
                         was requested), otherwise empty string.
    """

    source_lang: str
    target_lang: str
    original_text: str
    translated_text: str
    timestamp: str
    detected_lang: str = ""
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.original_text)
