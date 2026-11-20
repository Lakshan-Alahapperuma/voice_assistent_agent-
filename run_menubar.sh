#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "/Users/lakshanalahapperuma/agentic-ai" || exit 1
mkdir -p "$HOME/.nova"
exec "/Users/lakshanalahapperuma/agentic-ai/.venv/bin/python3" "/Users/lakshanalahapperuma/agentic-ai/main.py" --menubar >> "$HOME/.nova/menubar.log" 2>&1
