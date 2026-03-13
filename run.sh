#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/venv"

echo "=== Seeru Book - Gift Tracker ==="

# Create venv if needed
if [ ! -d "$VENV" ]; then
  echo "Setting up virtual environment..."
  python3 -m venv "$VENV"
fi

# Install dependencies
echo "Checking dependencies..."
"$VENV/bin/pip" install -q flask openpyxl

echo ""
echo "Starting app at http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

cd "$DIR"
"$VENV/bin/python" app.py
