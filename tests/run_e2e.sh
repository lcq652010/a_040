#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON="python3"
if ! command -v python3 &>/dev/null; then
    PYTHON="python"
fi

if ! $PYTHON -c "import requests" &>/dev/null; then
    echo "Installing requests..."
    $PYTHON -m pip install requests --quiet
fi

ARGS=()
for arg in "$@"; do
    ARGS+=("$arg")
done

echo "============================================"
echo " PHM System E2E Test Launcher (Linux/Mac)"
echo "============================================"
echo " Project : $PROJECT_ROOT"
echo " Python  : $PYTHON"
echo " Args    : ${ARGS[*]:-none}"
echo "============================================"
echo

cd "$PROJECT_ROOT"
$PYTHON "$SCRIPT_DIR/e2e_test.py" "${ARGS[@]}"
