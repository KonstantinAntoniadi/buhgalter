#!/bin/bash
SCRIPT_DIR=$(dirname "$(realpath "$0")")

cd "$SCRIPT_DIR" || exit 1
source "$SCRIPT_DIR/.venv/bin/activate"
cd buhgalter
python3 get_balance.py
deactivate