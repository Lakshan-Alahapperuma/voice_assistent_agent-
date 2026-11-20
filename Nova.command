#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
nohup "$DIR/.venv/bin/python3" "$DIR/main.py" --menubar > /dev/null 2>&1 &
