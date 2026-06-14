"""
app.py — AI Language Translator · Main Streamlit Application

Entry point for the web application.  All UI logic lives here;
translation and TTS logic is delegated to translator.py.

Run:
    streamlit run app.py --server.port 5000
"""

from __future__ import annotations

import datetime
import io
import logging
import os
import sys
import zipfile

# ---------------------------------------------------------------------------
# Path setup — allow sibling imports when running from the workspace root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from config import (
    ALLOWED_UPLOAD_EXTENSIONS,
    APP_DESCRIPTION,
    APP_ICON,
    APP_NAME,
    APP_VERSION,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    HISTORY_MAX_ENTRIES,
    MAX_FILE_SIZE_BYTES,
    MAX_INPUT_CHARS,
    SOURCE_LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    TARGET_LANGUAGE_NAMES,
    TranslationRecord,
    setup_logging,
)
from translator import (
    count_words,
    detect_language,
    extract_text_from_file,
    generate_tts_audio,
    get_language_name,
    translate_text,
)

# ---------------------------------------------------------------------------
# Logging initialisation (runs once per interpreter lifecycle)
# ---------------------------------------------------------------------------
logger = setup_logging(logging.INFO)

# ---------------------------------------------------------------------------
# Streamlit page configuration — MUST be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": f"**{APP_NAME}** v{APP_VERSION}\n\n{APP_DESCRIPTION}",
    },
)


# ===========================================================================
# Session-state helpers
# ===========================================================================

def _init_session_state() -> None:
    """Initialise all session-state keys exactly once per session."""
    defaults: dict = {
        "translation_history": [],   # list[TranslationRecord]
        "last_translated_text": "",
        "last_translation_result": "",
        "detected_language_name": "",
        "tts_audio_bytes": None,
        "show_history": True,
        "translate_triggered": False,
        # File upload
        "last_uploaded_filename": "",  # tracks which file was last loaded
        "file_char_count": 0,          # character count of the loaded file
        "file_word_count": 0,          # word count of the loaded file
        # Download translation
        "last_target_lang_name": "",   # human-readable target language for filename
        # Project ZIP
        "_zip_bytes": None,
        "_zip_filename": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ===========================================================================
# Project ZIP download
# ===========================================================================

# Files/dirs to exclude from the project ZIP
_ZIP_EXCLUDE_PATTERNS: tuple[str, ...] = (
    "__pycache__",
    ".pyc",
    ".pyo",
    ".gitkeep",
    ".DS_Store",
)

def build_project_zip() -> bytes:
    """Bundle the entire AI_Language_Translator project into a ZIP archive.

    Walks the directory where this script lives, skipping byte-compiled
    files and cache folders.  Returns the archive as raw bytes so it can
    be passed directly to ``st.download_button``.

    Returns:
        Raw ZIP bytes ready for download.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    project_name = os.path.basename(project_root)  # "AI_Language_Translator"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(project_root):
            # Skip excluded directories in-place so os.walk doesn't recurse into them
            dirnames[:] = [
                d for d in dirnames
                if not any(pat in d for pat in _ZIP_EXCLUDE_PATTERNS)
            ]

            for filename in filenames:
                # Skip excluded file patterns
                if any(pat in filename for pat in _ZIP_EXCLUDE_PATTERNS):
                    continue

                full_path = os.path.join(dirpath, filename)
                # Arc name preserves the folder structure inside the ZIP
                arc_name = os.path.join(
                    project_name,
                    os.path.relpath(full_path, project_root),
                )
                zf.write(full_path, arc_name)

    buffer.seek(0)
    zip_bytes = buffer.read()
    logger.info("Project ZIP built: %d bytes, %d files", len(zip_bytes), len(zf.infolist()))
    return zip_bytes


# ===========================================================================
# Sidebar
# ===========================================================================

def render_sidebar() -> tuple[str, str]:
    """Render the language-selection sidebar.

    Returns:
        Tuple of (source_lang_code, target_lang_code) as ISO strings.
    """
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_NAME}")
        st.caption(f"v{APP_VERSION} · Powered by Google Translate")
        st.divider()

        st.subheader("⚙️ Language Settings")

        # --- Source language ---
        src_idx = SOURCE_LANGUAGE_NAMES.index(DEFAULT_SOURCE_LANGUAGE)
        source_lang_name: str = st.selectbox(
            "🔍 Source Language",
            options=SOURCE_LANGUAGE_NAMES,
            index=src_idx,
            help=(
                "Choose the language of your input text, or select "
                "**Auto-Detect** to let the engine identify it automatically."
            ),
        )

        # --- Target language ---
        tgt_idx = TARGET_LANGUAGE_NAMES.index(DEFAULT_TARGET_LANGUAGE)
        target_lang_name: str = st.selectbox(
            "🎯 Target Language",
            options=TARGET_LANGUAGE_NAMES,
            index=tgt_idx,
            help="The language you want the text translated into.",
        )

        # Guard against identical source ↔ target (excluding auto-detect)
        src_code = SUPPORTED_LANGUAGES[source_lang_name]
        tgt_code = SUPPORTED_LANGUAGES[target_lang_name]

        if src_code != "auto" and src_code == tgt_code:
            st.warning(
                "⚠️ Source and target languages are the same. "
                "The text will be returned unchanged."
            )

        st.divider()

        # --- History toggle ---
        st.subheader("📜 History")
        st.session_state.show_history = st.toggle(
            "Show translation history",
            value=st.session_state.show_history,
        )

        history_count = len(st.session_state.translation_history)
        st.caption(f"{history_count} / {HISTORY_MAX_ENTRIES} entries stored")

        if history_count > 0:
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.translation_history = []
                st.rerun()

        st.divider()

        # --- Download Project ZIP ---
        st.subheader("📦 Download Project")
        st.caption("Get the full source code as a ZIP for GitHub or portfolio submission.")

        zip_filename = (
            f"AI_Language_Translator_"
            f"{datetime.datetime.now().strftime('%Y%m%d')}.zip"
        )

        if st.button("🗜️ Build & Download ZIP", use_container_width=True):
            with st.spinner("Packaging project files..."):
                zip_bytes = build_project_zip()
            st.session_state["_zip_bytes"] = zip_bytes
            st.session_state["_zip_filename"] = zip_filename
            st.rerun()

        # Render the download button once ZIP bytes are ready
        if st.session_state.get("_zip_bytes"):
            st.download_button(
                label="⬇️ Save ZIP to your computer",
                data=st.session_state["_zip_bytes"],
                file_name=st.session_state.get("_zip_filename", zip_filename),
                mime="application/zip",
                use_container_width=True,
                help="Downloads the complete AI_Language_Translator project folder",
            )
            kb = len(st.session_state["_zip_bytes"]) // 1024
            st.caption(f"Ready — {kb} KB  |  includes all source files")

        st.divider()

        # --- About ---
        with st.expander("ℹ️ About"):
            st.markdown(
                f"""
                **{APP_NAME}** translates text between 50+ languages
                using the Google Translate API via **deep-translator**.

                🔊 Text-to-speech is powered by **gTTS**.

                📦 Source code is available via the **Download Project** button above.

                📋 Features:
                - Automatic language detection
                - File upload (.txt / .docx)
                - Session translation history
                - Audio playback of results
                - One-click project ZIP export
                """
            )

    return src_code, tgt_code


# ===========================================================================
# Main content area
# ===========================================================================

def render_header() -> None:
    """Display the page title and description."""
    col_title, col_badge = st.columns([4, 1])
    with col_title:
        st.title(f"{APP_ICON} {APP_NAME}")
        st.markdown(
            f"*{APP_DESCRIPTION}*",
            help="Supports 50+ languages with automatic detection.",
        )
    with col_badge:
        st.markdown(
            f"""
            <div style="text-align:right; margin-top:16px;">
                <span style="
                    background:#4F8EF7;
                    color:white;
                    padding:4px 10px;
                    border-radius:20px;
                    font-size:0.75rem;
                    font-weight:600;
                    letter-spacing:0.05em;
                ">v{APP_VERSION}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.divider()


def render_input_section() -> str:
    """Render the tabbed input area (type/paste OR upload file).

    Returns:
        The text to be translated — either what the user typed or what
        was extracted from an uploaded file.
    """
    tab_type, tab_upload = st.tabs(["✍️ Type / Paste", "📂 Upload File"])

    # ------------------------------------------------------------------
    # Tab 1 — manual text input
    # ------------------------------------------------------------------
    with tab_type:
        input_text: str = st.text_area(
            label="Input Text",
            placeholder="Type or paste the text you want to translate here...",
            height=180,
            max_chars=MAX_INPUT_CHARS,
            label_visibility="collapsed",
            key="input_text_area",
        )

        char_count = len(input_text)
        word_count = count_words(input_text)

        col_counter, col_tip = st.columns([2, 3])
        with col_counter:
            st.caption(
                f"📊 {char_count:,} / {MAX_INPUT_CHARS:,} characters - {word_count:,} words"
            )
        with col_tip:
            if char_count == 0:
                st.caption("💡 Tip: Use **Auto-Detect** in the sidebar for unknown languages.")

    # ------------------------------------------------------------------
    # Tab 2 — file upload
    # ------------------------------------------------------------------
    with tab_upload:
        _render_file_uploader()

    # Return whichever source has content.  If the user loaded a file
    # it was written into the session-state key for the text_area, so
    # `input_text` already reflects it on the next render cycle.
    return input_text


def _render_file_uploader() -> None:
    """Render the file uploader widget and populate the text area on upload.

    Supports .txt and .docx files up to MAX_FILE_SIZE_BYTES.
    When a new file is detected it extracts the text, writes it into
    ``st.session_state["input_text_area"]``, and triggers a rerun so
    the Type/Paste tab shows the pre-filled content ready to translate.
    """
    st.markdown("**Upload a document to translate**")
    st.caption(
        f"Supported formats: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)} "
        f"- Max size: {MAX_FILE_SIZE_BYTES // 1_000} KB"
    )

    uploaded = st.file_uploader(
        label="Choose a file",
        type=[ext.lstrip(".") for ext in ALLOWED_UPLOAD_EXTENSIONS],
        label_visibility="collapsed",
        key="file_uploader",
    )

    if uploaded is None:
        # No file chosen yet — show a helpful hint
        st.info(
            "📌 After uploading, the extracted text will appear in the "
            "**Type / Paste** tab where you can review or edit it before translating."
        )
        st.session_state.last_uploaded_filename = ""
        return

    # Detect when a genuinely new file has been chosen
    is_new_file = uploaded.name != st.session_state.get("last_uploaded_filename", "")

    if is_new_file:
        file_bytes = uploaded.read()

        # --- Size guard ---
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            st.error(
                f"File is too large ({len(file_bytes) // 1_000:,} KB). "
                f"Maximum allowed size is {MAX_FILE_SIZE_BYTES // 1_000:,} KB."
            )
            return

        with st.spinner(f"Reading '{uploaded.name}'..."):
            extracted, error = extract_text_from_file(file_bytes, uploaded.name)

        if error:
            st.error(f"Could not read file: {error}")
            logger.warning("File extraction failed for '%s': %s", uploaded.name, error)
            return

        if not extracted.strip():
            st.warning("The file appears to be empty or contains no readable text.")
            return

        # Truncate to the character limit and warn the user
        truncated = False
        if len(extracted) > MAX_INPUT_CHARS:
            extracted = extracted[:MAX_INPUT_CHARS]
            truncated = True

        # Write extracted text into the shared text-area key so it
        # appears pre-filled when the user switches to the Type/Paste tab
        st.session_state["input_text_area"] = extracted
        st.session_state["last_uploaded_filename"] = uploaded.name
        st.session_state["file_char_count"] = len(extracted)
        st.session_state["file_word_count"] = count_words(extracted)

        # Clear any stale TTS audio from a previous translation
        st.session_state["tts_audio_bytes"] = None

        logger.info(
            "File loaded: '%s' — %d chars, %d words",
            uploaded.name,
            len(extracted),
            count_words(extracted),
        )

        if truncated:
            st.warning(
                f"The file was truncated to the {MAX_INPUT_CHARS:,}-character limit. "
                "The remaining text was not loaded."
            )

        st.rerun()

    # File already loaded — show a summary card
    char_c = st.session_state.get("file_char_count", 0)
    word_c = st.session_state.get("file_word_count", 0)

    st.success(f"**{uploaded.name}** loaded successfully")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Characters", f"{char_c:,}")
    col_b.metric("Words", f"{word_c:,}")
    col_c.metric("Format", uploaded.name.rsplit(".", 1)[-1].upper())
    st.caption("Switch to the **Type / Paste** tab to review or edit the text, then click Translate.")


def render_translate_button() -> bool:
    """Render the Translate button and return True when it is clicked."""
    col_btn, col_spacer = st.columns([1, 4])
    with col_btn:
        clicked = st.button(
            "🌐 Translate",
            use_container_width=True,
            type="primary",
        )
    return clicked


def perform_translation(
    input_text: str,
    src_code: str,
    tgt_code: str,
    source_lang_name: str,
    target_lang_name: str,
) -> None:
    """Run the translation pipeline and update session state.

    Args:
        input_text:       Raw text from the input area.
        src_code:         ISO source language code (or "auto").
        tgt_code:         ISO target language code.
        source_lang_name: Human-readable source language name.
        target_lang_name: Human-readable target language name.
    """
    stripped = input_text.strip()

    # Validate: non-empty input
    if not stripped:
        st.warning("⚠️ Please enter some text before translating.")
        return

    with st.spinner("🔄 Translating…  please wait"):
        result = translate_text(stripped, src_code, tgt_code)

    if not result.success:
        st.error(f"❌ Translation failed: {result.error_message}")
        logger.warning("Translation failed: %s", result.error_message)
        return

    # --- Persist results to session state ---
    st.session_state.last_translated_text = stripped
    st.session_state.last_translation_result = result.translated_text
    st.session_state.last_target_lang_name = target_lang_name
    st.session_state.tts_audio_bytes = None  # reset audio for new translation

    # Resolve detected language display name
    if result.detected_lang:
        detected_name = get_language_name(result.detected_lang)
        st.session_state.detected_language_name = detected_name
    else:
        st.session_state.detected_language_name = ""

    # --- Add to history ---
    record = TranslationRecord(
        source_lang=source_lang_name,
        target_lang=target_lang_name,
        original_text=stripped,
        translated_text=result.translated_text,
        timestamp=datetime.datetime.now().strftime("%H:%M:%S"),
        detected_lang=result.detected_lang,
    )
    history: list[TranslationRecord] = st.session_state.translation_history
    history.insert(0, record)
    # Trim to maximum allowed entries
    st.session_state.translation_history = history[:HISTORY_MAX_ENTRIES]

    logger.info(
        "Translation stored in history. Total entries: %d",
        len(st.session_state.translation_history),
    )

    # Display a brief success metric
    st.success(
        f"✅ Translated in **{result.elapsed_seconds:.2f}s** - "
        f"{result.char_count:,} characters processed."
    )


def _build_download_content(translated: str, tgt_lang_name: str) -> tuple[bytes, str]:
    """Build the download payload and suggested filename.

    Args:
        translated:    The translated text to embed in the file.
        tgt_lang_name: Human-readable target language name.

    Returns:
        Tuple of (utf-8 encoded bytes, suggested filename string).
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_lang = tgt_lang_name.replace(" ", "_").replace("(", "").replace(")", "")
    filename = f"translation_{safe_lang}_{timestamp}.txt"
    content = (
        f"AI Language Translator — Result\n"
        f"{'=' * 40}\n"
        f"Target language : {tgt_lang_name}\n"
        f"Exported at     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'=' * 40}\n\n"
        f"{translated}\n"
    )
    return content.encode("utf-8"), filename


def render_output_section(tgt_code: str) -> None:
    """Render the translated text output, download button, copy hint, and TTS.

    Args:
        tgt_code: ISO code of the target language (used for TTS).
    """
    translated = st.session_state.get("last_translation_result", "")
    if not translated:
        return

    st.divider()
    st.subheader("✨ Translation Result")

    # Detected language badge (only shown when auto-detect was used)
    detected_name = st.session_state.get("detected_language_name", "")
    if detected_name:
        st.info(f"🔍 Detected source language: **{detected_name}**")

    # Output text box (read-only via disabled text_area)
    st.text_area(
        label="Translated Text",
        value=translated,
        height=180,
        disabled=True,
        label_visibility="collapsed",
        key="output_text_area",
    )

    # Action row: download | TTS | copy hint
    col_dl, col_tts, col_copy = st.columns([2, 2, 3])

    tgt_lang_name = st.session_state.get("last_target_lang_name", "Translation")

    with col_dl:
        file_bytes, filename = _build_download_content(translated, tgt_lang_name)
        st.download_button(
            label="⬇️ Download (.txt)",
            data=file_bytes,
            file_name=filename,
            mime="text/plain; charset=utf-8",
            use_container_width=True,
            help="Save the translated text as a .txt file",
        )

    with col_tts:
        if st.button("🔊 Listen (Text-to-Speech)", use_container_width=True):
            _handle_tts(translated, tgt_code)

    with col_copy:
        st.caption("📋 Select all text above, then **Ctrl+A → Ctrl+C** (or ⌘ on Mac) to copy.")

    # Render audio player if bytes are already generated
    audio_bytes = st.session_state.get("tts_audio_bytes")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
        st.caption("🎵 Audio generated via Google Text-to-Speech (gTTS).")


def _handle_tts(text: str, lang_code: str) -> None:
    """Generate and cache TTS audio for *text* in *lang_code*.

    Args:
        text:      The text to synthesise.
        lang_code: ISO target language code.
    """
    with st.spinner("🔊 Generating audio…"):
        audio_bytes = generate_tts_audio(text, lang_code)

    if audio_bytes:
        st.session_state.tts_audio_bytes = audio_bytes
        st.rerun()
    else:
        st.warning(
            "⚠️ Text-to-speech is not available for this language, "
            "or the audio service could not be reached.  "
            "Please try a different language."
        )


# ===========================================================================
# Translation history
# ===========================================================================

def render_history() -> None:
    """Display the session translation history table."""
    if not st.session_state.show_history:
        return

    history: list[TranslationRecord] = st.session_state.translation_history
    if not history:
        return

    st.divider()
    st.subheader("📜 Translation History")
    st.caption(
        f"Showing the last {len(history)} translation(s) from this session.  "
        "History is cleared when you close the browser tab."
    )

    for i, record in enumerate(history):
        # Build a short preview of the original text
        preview_original = (
            record.original_text[:60] + "…"
            if len(record.original_text) > 60
            else record.original_text
        )
        preview_translated = (
            record.translated_text[:60] + "…"
            if len(record.translated_text) > 60
            else record.translated_text
        )

        with st.expander(
            f"🕐 {record.timestamp}  |  "
            f"{record.source_lang} -> {record.target_lang}  |  "
            f'"{preview_original}"',
            expanded=(i == 0),
        ):
            col_orig, col_arrow, col_trans = st.columns([5, 1, 5])
            with col_orig:
                st.markdown(f"**{record.source_lang}**")
                st.text_area(
                    label=f"original_{i}",
                    value=record.original_text,
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"hist_orig_{i}",
                )
            with col_arrow:
                st.markdown(
                    "<div style='text-align:center;margin-top:40px;font-size:1.4rem;'>→</div>",
                    unsafe_allow_html=True,
                )
            with col_trans:
                st.markdown(f"**{record.target_lang}**")
                st.text_area(
                    label=f"translated_{i}",
                    value=record.translated_text,
                    height=100,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"hist_trans_{i}",
                )

            meta_parts = [f"⏱ {record.char_count:,} chars"]
            if record.detected_lang:
                meta_parts.append(f"🔍 Detected: {get_language_name(record.detected_lang)}")
            st.caption("  |  ".join(meta_parts))


# ===========================================================================
# Quick-translation shortcuts (swap languages hint)
# ===========================================================================

def render_tips_section() -> None:
    """Render a collapsible usage-tips section."""
    with st.expander("💡 Tips & Shortcuts", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                """
                **Getting started**
                - Type or paste text in the **Type / Paste** tab
                - Or upload a `.txt` / `.docx` file via the **Upload File** tab
                - Pick languages in the left sidebar
                - Click **🌐 Translate**
                - Use **Auto-Detect** when unsure of the source language

                **Text-to-Speech**
                - Click **🔊 Listen** after translating
                - Audio plays inline — no download needed
                - Works with 40+ languages via Google TTS
                """
            )
        with col2:
            st.markdown(
                """
                **File upload**
                - Supports `.txt` (any encoding) and `.docx` (Word)
                - Max file size: 500 KB
                - Text is loaded into the editor so you can review before translating
                - Files longer than 5,000 characters are automatically trimmed

                **Copy the translation**
                - Click inside the result box
                - Press **Ctrl+A** then **Ctrl+C** (Windows/Linux)
                - Or **⌘+A** then **⌘+C** (macOS)

                **History**
                - All translations are saved for this session
                - Toggle visibility with the sidebar switch
                - Expand any row to see the full text
                """
            )


# ===========================================================================
# Application entry point
# ===========================================================================

def main() -> None:
    """Orchestrate the full Streamlit application layout."""
    _init_session_state()

    # Sidebar (returns language codes)
    src_code, tgt_code = render_sidebar()

    # Resolve human-readable names for history records
    source_lang_name = next(
        (k for k, v in SUPPORTED_LANGUAGES.items() if v == src_code),
        src_code,
    )
    target_lang_name = next(
        (k for k, v in SUPPORTED_LANGUAGES.items() if v == tgt_code),
        tgt_code,
    )

    # Main content
    render_header()
    input_text = render_input_section()
    translate_clicked = render_translate_button()

    if translate_clicked:
        perform_translation(
            input_text=input_text,
            src_code=src_code,
            tgt_code=tgt_code,
            source_lang_name=source_lang_name,
            target_lang_name=target_lang_name,
        )

    render_output_section(tgt_code)
    render_history()
    render_tips_section()

    # Footer
    st.divider()
    st.caption(
        f"🌐 {APP_NAME} | Built with Streamlit & Google Translate API | "
        f"[deep-translator](https://github.com/nidhaloff/deep-translator) | "
        f"[gTTS](https://gtts.readthedocs.io/)"
    )


if __name__ == "__main__":
    main()
