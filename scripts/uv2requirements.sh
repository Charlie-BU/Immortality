#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ -f requirements.txt ]; then
    rm requirements.txt
fi

uv export --no-hashes --no-annotate --format=requirements.txt > requirements.txt
