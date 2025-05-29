#!/bin/bash

# Percorso assoluto dello script Python
SCRIPT_PATH="$(dirname "$(realpath "$0")")/yurind.py"

# Ambiente pulito, evita variabili che possono inquinare GI
env -u GTK_PATH -u GI_TYPELIB_PATH -u PYTHONPATH \
    python3 "$SCRIPT_PATH"
