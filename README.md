# NOVA — Local Autonomous AI Voice Assistant for macOS

Nova is a local, privacy-first personal AI agent for macOS built with Python and Ollama. Unlike typical chatbots, Nova is equipped with direct computer automation capabilities: it executes local system tasks, manages and organizes files, drafts and sends emails, controls applications, and communicates via voice.

---

## Architecture Overview

```
                                      ┌─────────────────────────────────────┐
                                      │             User Voice              │
                                      └──────────────────┬──────────────────┘
                                                         │
                                               [ Wake Word: "Hey Nova" ]
                                                         │
                                                         ▼
                                      ┌─────────────────────────────────────┐
                                      │       faster-whisper (STT)          │
                                      │   Converts speech to prompt text    │
                                      └──────────────────┬──────────────────┘
                                                         │
                                                         ▼
                                      ┌─────────────────────────────────────┐
                                      │      Local AI Brain — Ollama        │
                                      │     (qwen2.5:3b / qwen3:4b)         │
                                      └──────────────────┬──────────────────┘
                                                         │
                         ┌───────────────────────────────┴───────────────────────────────┐
                         ▼                               ▼                               ▼
              ┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
              │      File Agent     │         │      Mac Agent      │         │     Email Agent     │
              │  • Search files     │         │  • Open apps        │         │  • Draft in Mail    │
              │  • Safe write/diff  │         │  • Volume control   │         │  • Send approval    │
              │  • Organize folders │         │  • System stats     │         │  • Contact lookup   │
              │  • Auto-backups     │         │  • AppleScript      │         │                     │
              └──────────┬──────────┘         └──────────┬──────────┘         └──────────┬──────────┘
                         │                               │                               │
                         └───────────────────────────────┼───────────────────────────────┘
                                                         │
                                                         ▼
                                      ┌─────────────────────────────────────┐
                                      │    Safety & Guardrails (Approval)   │
                                      └──────────────────┬──────────────────┘
                                                         │
                                                         ▼
                                      ┌─────────────────────────────────────┐
                                      │         macOS TTS (`say`)           │
                                      │  Spoken feedback in natural voice   │
                                      └─────────────────────────────────────┘
```

---

## Features

- **Local & Private:** Runs 100% on your Mac using local LLMs via Ollama. No third-party API keys or subscription fees required.
- **Autonomous Tool Execution:** Automatically selects and invokes tools (file handling, macOS controls, development commands, email).
- **Safety by Default:** Destructive actions (overwriting files, sending emails, executing shell commands) require explicit human approval.
- **Automated Backups:** Any modified file is backed up with timestamping in `~/.nova/backups/`.
- **macOS Native Voice:** High-fidelity spoken feedback using macOS's built-in speech engine (`say`) with over 60+ customizable voices.
- **Persistent Memory:** SQLite-backed interaction history, task logs, and user preferences stored in `~/.nova/memory.db`.

---

## Quick Start (Phase 1)

### 1. Prerequisites
Ensure you have Homebrew and Python 3.11+ installed:
```bash
brew install ollama
```

### 2. Start Ollama and Download a Model
In a separate terminal window, launch the Ollama service:
```bash
ollama serve
```

In another terminal window, pull your chosen model (e.g. Qwen 2.5 3B or 7B):
```bash
ollama pull qwen2.5:3b
```

### 3. Setup Virtual Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run System Diagnostics
Verify that your environment, Ollama connection, and macOS voice engine are ready:
```bash
python main.py --check-system
```

### 5. Launch Nova
Run Nova in interactive text mode:
```bash
python main.py
```

Or enable voice responses:
```bash
python main.py --voice
```

---

## What You Can Ask Nova To Do

### 1. File Access & Organization
- *"Find all PDF files in my Documents folder."*
- *"Organize my Downloads folder into neat categories."* (Nova will preview the file movements first!)
- *"Create a meeting notes file on my Desktop named notes.txt with today's action items."*
- *"Read the first 50 lines of project_plan.md."*

### 2. Mac Automation
- *"Open Safari and Spotify."*
- *"Set system volume to 40%."*
- *"Show me system diagnostics and disk space."*
- *"Send a macOS notification that our build has completed."*

### 3. Email Integration
- *"Draft an email to my manager with the subject 'Weekly Update' saying the deliverables are ready."*
  - Nova creates the message and automatically opens it in macOS Mail for your review.

### 4. Development Tasks
- *"Run pytest and explain the results."*
- *"Check git status in this repository."*

---

## Phase 2: Adding Voice & Wake Word

To enable push-to-talk microphone input and faster-whisper speech recognition:

```bash
pip install -r requirements-voice.txt
```

Run with voice enabled:
```bash
python main.py --voice
```

---

## Configuration & Customization

Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `NOVA_MODEL` | `qwen2.5:3b` | Model name pulled in Ollama |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama daemon endpoint |
| `NOVA_VOICE` | `Samantha` | macOS speech voice (`say -v ?` to list) |
| `NOVA_SPEECH_RATE` | `190` | Words per minute |
| `NOVA_AUTO_CONFIRM_SAFE` | `True` | Auto-confirm non-destructive actions |

---

## Running Automated Tests

Run the full unit test suite:
```bash
.venv/bin/python3 -m unittest discover tests
```
