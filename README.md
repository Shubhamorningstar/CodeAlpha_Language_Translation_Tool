# 🌐 AI Language Translator

> A modern, professional AI-powered language translation web application built with Python and Streamlit.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?logo=streamlit)](https://streamlit.io)
[![deep-translator](https://img.shields.io/badge/deep--translator-1.11+-green)](https://github.com/nidhaloff/deep-translator)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 Project Overview

**AI Language Translator** is a full-featured, browser-based translation tool that lets users translate text between 50+ languages instantly.  It leverages Google's Translation API (via the `deep-translator` library) for accurate results, `gTTS` for browser-playable audio, and `langdetect` for automatic source-language identification — all wrapped in a polished Streamlit interface.

This project was designed as a showcase of:
- Clean, modular Python architecture
- Professional UI/UX with Streamlit
- Robust error handling and logging
- Production-ready code quality suitable for an AI internship portfolio

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔤 **Text Translation** | Translate up to 5,000 characters at a time between 50+ languages |
| 🔍 **Auto Language Detection** | Automatically identifies the source language using `langdetect` |
| 🔊 **Text-to-Speech** | Listen to the translated text via Google TTS (gTTS) |
| 📋 **Copy Support** | Select-all shortcut hint for fast clipboard copy |
| 📜 **Session History** | Stores the last 20 translations with expand/collapse view |
| ⚡ **Performance Metrics** | Shows translation time and character count after each call |
| 🛡️ **Error Handling** | Graceful messages for network errors, empty input, and unsupported pairs |
| 📊 **Live Character Counter** | Real-time character and word count as you type |
| 💡 **Usage Tips** | Collapsible tips panel for keyboard shortcuts and best practices |

---

## 🛠️ Technologies Used

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.32 | Web application framework |
| `deep-translator` | ≥ 1.11 | Google Translate API wrapper |
| `gtts` | ≥ 2.5 | Google Text-to-Speech audio generation |
| `pyttsx3` | ≥ 2.90 | Offline TTS engine (desktop use) |
| `langdetect` | ≥ 1.0.9 | Statistical language detection |
| Python | 3.11 | Core runtime |

---

## 📁 Project Structure

```
AI_Language_Translator/
│
├── app.py              ← Main Streamlit application (UI logic)
├── translator.py       ← Translation & TTS engine (no UI dependency)
├── config.py           ← Centralised config, constants, data models
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
│
├── .streamlit/
│   └── config.toml     ← Streamlit server & theme configuration
│
└── assets/             ← Static assets (screenshots, logos, etc.)
```

### Module responsibilities

- **`app.py`** — Streamlit page layout, session state management, button callbacks, and rendering functions. Delegates all business logic to `translator.py`.
- **`translator.py`** — Pure-Python translation and TTS logic. No Streamlit imports — fully testable in isolation.
- **`config.py`** — Single source of truth for language catalogues, UI constants, logging setup, and the `TranslationRecord` dataclass.

---

## ⚙️ Installation

### Prerequisites

- Python 3.10+ (3.11 recommended)
- `pip` (bundled with Python)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/ai-language-translator.git
cd ai-language-translator/AI_Language_Translator

# 2. (Recommended) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## 🚀 Usage Guide

1. **Enter text** — Type or paste up to 5,000 characters in the input area.
2. **Select languages** — Use the **sidebar** to choose source and target languages.
   - Select **Auto-Detect** as source to let the app identify the language automatically.
3. **Translate** — Click the **🌐 Translate** button.
4. **View results** — The translated text appears in the output section.
5. **Listen** — Click **🔊 Listen (Text-to-Speech)** to hear the translation.
6. **Copy** — Click inside the result box and press **Ctrl+A → Ctrl+C** (or ⌘ on Mac).
7. **Review history** — All translations for the current session appear in the **📜 Translation History** section below.

---

## 📸 Screenshots

> _Add screenshots here after running the application._

| Input & Language Selection | Translation Output | Translation History |
|---|---|---|
| _(screenshot)_ | _(screenshot)_ | _(screenshot)_ |

---

## 🔧 Configuration

The `.streamlit/config.toml` file controls server settings and the dark theme:

```toml
[server]
headless = true
address  = "0.0.0.0"
port     = 5000

[theme]
primaryColor           = "#4F8EF7"
backgroundColor        = "#0E1117"
secondaryBackgroundColor = "#1A1F2E"
textColor              = "#FAFAFA"
```

All application-level constants (character limits, supported languages, default selections) live in `config.py` and can be adjusted without touching the UI code.

---

## 🧪 Running Tests

The translation logic in `translator.py` has no Streamlit dependency and can be tested with standard frameworks:

```bash
pip install pytest
pytest tests/        # (add tests/ directory as needed)
```

---

## 🚧 Future Improvements

- [ ] **Batch translation** — translate multiple sentences/documents at once
- [ ] **File upload** — translate `.txt` and `.docx` files
- [ ] **Pronunciation guide** — show phonetic transcription for CJK and Arabic
- [ ] **Confidence score** — display detection confidence from `langdetect`
- [ ] **Persistent history** — save history to SQLite across sessions
- [ ] **Keyboard shortcut** — `Ctrl+Enter` to trigger translation
- [ ] **Dark / light theme toggle** — user-selectable theme
- [ ] **API key support** — allow users to supply their own Google API key for higher quotas
- [ ] **REST API mode** — expose translation as a FastAPI endpoint for programmatic access
- [ ] **Unit test suite** — full pytest coverage for `translator.py` and `config.py`

---

## 👤 Author

Built as a professional AI internship portfolio project.

- **GitHub:** [github.com/your-username](https://github.com/your-username)
- **LinkedIn:** [linkedin.com/in/your-profile](https://linkedin.com/in/your-profile)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [deep-translator](https://github.com/nidhaloff/deep-translator) — elegant Google Translate wrapper
- [gTTS](https://github.com/pndurette/gTTS) — Google Text-to-Speech Python library
- [Streamlit](https://streamlit.io) — the fastest way to build Python data apps
- [langdetect](https://github.com/Mimino666/langdetect) — language detection ported from Google's language-detection library
