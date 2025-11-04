#!/bin/bash
cd "$(dirname "$0")"

if [[ "$1" == "-l" || "$1" == "--local" ]]; then
    source ../.venv/bin/activate
fi

pip install -r requirements.txt
python app.py