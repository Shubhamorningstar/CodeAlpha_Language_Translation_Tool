"""
translator.py — Core translation and text-to-speech logic.

This module is intentionally kept free of Streamlit imports so it can
be unit-tested or reused in other contexts.

Public API
----------
translate_text(text, source_lang_code, target_lang_code) -> TranslationResult
detect_language(text) -> str
generate_tts_audio(text, lang_code) -> bytes | None
get_language_name(lang_code) -> str
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    LanguageNotSupportedException,
    TranslationNotFound,
)

logger = logging.getLogger("AI Language Translator.translator")


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class TranslationResult:
    """Holds the outcome of a single translation request.

    Attributes:
        success:          True if the translation completed without error.
        translated_text:  The translated output; empty string on failure.
        detected_lang:    ISO code of the detected source language
                          (non-empty only when source was "auto").
        error_message:    Human-readable error description; empty on success.
        elapsed_seconds:  Wall-clock time taken by the API call.
        char_count:       Number of characters in the original input.
    """

    success: bool
    translated_text: str = ""
    detected_lang: str = ""
    error_message: str = ""
    elapsed_seconds: float = 0.0
    char_count: int = field(default=0, repr=False)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def translate_text(
    text: str,
    source_lang_code: str,
    target_lang_code: str,
) -> TranslationResult:
    """Translate *text* from *source_lang_code* to *target_lang_code*.

    Args:
        text:             The text to translate.  Must be non-empty.
        source_lang_code: ISO 639-1 code (e.g. "en") or "auto" for
                          automatic language detection.
        target_lang_code: ISO 639-1 code for the desired output language.

    Returns:
        A :class:`TranslationResult` instance.  On failure, ``success``
        is ``False`` and ``error_message`` is populated.
    """
    text = text.strip()
    if not text:
        return TranslationResult(
            success=False,
            error_message="Input text is empty. Please enter something to translate.",
        )

    logger.info(
        "Translating %d chars | source=%s → target=%s",
        len(text),
        source_lang_code,
        target_lang_code,
    )

    start = time.perf_counter()

    try:
        translator = GoogleTranslator(
            source=source_lang_code,
            target=target_lang_code,
        )
        translated = translator.translate(text)
        elapsed = time.perf_counter() - start

        if not translated:
            return TranslationResult(
                success=False,
                error_message="The translation engine returned an empty response. Please try again.",
                elapsed_seconds=elapsed,
                char_count=len(text),
            )

        # deep-translator exposes the detected language on the translator
        # object after a successful call when source is "auto".
        detected = ""
        if source_lang_code == "auto":
            detected = _detect_language_safe(text)

        logger.info(
            "Translation complete in %.2fs (detected=%s)",
            elapsed,
            detected or "n/a",
        )

        return TranslationResult(
            success=True,
            translated_text=translated,
            detected_lang=detected,
            elapsed_seconds=elapsed,
            char_count=len(text),
        )

    except LanguageNotSupportedException as exc:
        logger.warning("Unsupported language pair: %s", exc)
        return TranslationResult(
            success=False,
            error_message=(
                f"Language not supported: {exc}. "
                "Please try a different language pair."
            ),
            elapsed_seconds=time.perf_counter() - start,
        )

    except TranslationNotFound as exc:
        logger.warning("Translation not found: %s", exc)
        return TranslationResult(
            success=False,
            error_message=(
                "No translation was found for the given text. "
                "This can happen with very short inputs or special characters."
            ),
            elapsed_seconds=time.perf_counter() - start,
        )

    except ConnectionError as exc:
        logger.error("Network error during translation: %s", exc)
        return TranslationResult(
            success=False,
            error_message=(
                "Network error: Unable to reach the translation service. "
                "Please check your internet connection and try again."
            ),
            elapsed_seconds=time.perf_counter() - start,
        )

    except Exception as exc:  # noqa: BLE001 — broad catch is intentional here
        logger.error("Unexpected translation error: %s", exc, exc_info=True)
        return TranslationResult(
            success=False,
            error_message=f"An unexpected error occurred: {exc}",
            elapsed_seconds=time.perf_counter() - start,
        )


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    """Return the ISO 639-1 language code detected in *text*.

    Uses ``langdetect`` as the primary engine and falls back to a
    GoogleTranslator dry-run if ``langdetect`` is unavailable.

    Args:
        text: The text whose language should be detected.

    Returns:
        ISO 639-1 code (e.g. ``"en"``, ``"fr"``), or an empty string
        if detection fails.
    """
    return _detect_language_safe(text)


def _detect_language_safe(text: str) -> str:
    """Internal helper that swallows all exceptions."""
    if not text or not text.strip():
        return ""
    try:
        from langdetect import detect, LangDetectException  # type: ignore[import]

        try:
            code = detect(text.strip())
            logger.debug("langdetect result: %s", code)
            return code
        except LangDetectException:
            return ""
    except ImportError:
        pass

    # Fallback: let GoogleTranslator reveal the detected language via a
    # round-trip translation to English.
    try:
        translator = GoogleTranslator(source="auto", target="en")
        translator.translate(text[:200])
        return getattr(translator, "source", "") or ""
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------

def generate_tts_audio(text: str, lang_code: str) -> Optional[bytes]:
    """Generate MP3 audio bytes for *text* in *lang_code*.

    Uses gTTS (Google Text-to-Speech) to produce a browser-playable
    MP3 file returned as raw bytes.  pyttsx3 is listed in requirements
    for offline desktop use but is not suitable for web-server contexts
    because it directs output to the server's sound card, not the
    browser.  This function therefore uses gTTS exclusively.

    Args:
        text:      The text to convert to speech.
        lang_code: ISO 639-1 language code (e.g. ``"en"``, ``"fr"``).
                   Chinese variants (``"zh-CN"``, ``"zh-TW"``) are
                   normalised to ``"zh-CN"`` and ``"zh-TW"``
                   respectively.

    Returns:
        Raw MP3 bytes on success, or ``None`` if TTS is unavailable
        for the given language or an error occurs.
    """
    if not text or not text.strip():
        logger.warning("TTS called with empty text.")
        return None

    # Normalise Chinese variant codes that gTTS uses differently.
    normalised = _normalise_lang_for_tts(lang_code)

    logger.info("Generating TTS audio | lang=%s (normalised=%s)", lang_code, normalised)

    try:
        from gtts import gTTS, lang as gtts_lang  # type: ignore[import]

        # Verify the language is supported before attempting synthesis.
        supported = gtts_lang.tts_langs()
        if normalised not in supported:
            logger.warning(
                "TTS language '%s' not supported by gTTS (supported: %s…)",
                normalised,
                list(supported.keys())[:5],
            )
            return None

        tts = gTTS(text=text, lang=normalised, slow=False)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_bytes = buffer.read()
        logger.info("TTS audio generated: %d bytes", len(audio_bytes))
        return audio_bytes

    except ImportError:
        logger.error("gTTS is not installed.  Run: pip install gtts")
        return None

    except Exception as exc:  # noqa: BLE001
        logger.error("TTS generation failed: %s", exc, exc_info=True)
        return None


def _normalise_lang_for_tts(lang_code: str) -> str:
    """Map deep-translator language codes to gTTS-compatible codes."""
    mapping: dict[str, str] = {
        "iw": "iw",          # Hebrew
        "zh-CN": "zh-CN",
        "zh-TW": "zh-TW",
        "jw": "jw",          # Javanese
    }
    return mapping.get(lang_code, lang_code.split("-")[0])


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_language_name(lang_code: str) -> str:
    """Return the human-readable language name for an ISO 639-1 *lang_code*.

    Args:
        lang_code: ISO 639-1 code to look up.

    Returns:
        Human-readable name, or the original code if not found.
    """
    from config import SUPPORTED_LANGUAGES  # local import to avoid circular deps

    reverse_map = {v: k for k, v in SUPPORTED_LANGUAGES.items()}
    return reverse_map.get(lang_code, lang_code.upper())


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in *text*."""
    return len(text.split()) if text.strip() else 0


# ---------------------------------------------------------------------------
# File text extraction
# ---------------------------------------------------------------------------

def extract_text_from_file(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Extract plain text from an uploaded .txt or .docx file.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename including extension (used to detect format).

    Returns:
        A tuple of ``(extracted_text, error_message)``.  On success,
        ``error_message`` is empty.  On failure, ``extracted_text`` is
        empty and ``error_message`` describes what went wrong.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "txt":
        return _extract_txt(file_bytes)
    elif ext == "docx":
        return _extract_docx(file_bytes)
    else:
        return "", f"Unsupported file type '.{ext}'. Please upload a .txt or .docx file."


def _extract_txt(file_bytes: bytes) -> tuple[str, str]:
    """Decode a plain-text file, trying UTF-8 then latin-1 as fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            logger.info("Decoded .txt file with encoding=%s (%d chars)", encoding, len(text))
            return text, ""
        except UnicodeDecodeError:
            continue
    return "", "Could not decode the text file. Please ensure it is UTF-8 or plain ASCII."


def _extract_docx(file_bytes: bytes) -> tuple[str, str]:
    """Extract all paragraph text from a .docx Word document."""
    try:
        import io
        from docx import Document  # type: ignore[import]

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
        logger.info("Extracted %d paragraphs from .docx (%d chars)", len(paragraphs), len(text))
        return text, ""
    except ImportError:
        return "", "python-docx is not installed. Run: pip install python-docx"
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to extract .docx: %s", exc, exc_info=True)
        return "", f"Could not read the Word document: {exc}"
