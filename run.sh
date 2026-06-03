#!/usr/bin/env bash
# ========================================================
# TIPPSS SafeGuard-PQ Dashboard Launcher (Mac/Linux)
# ========================================================
set -e

echo ""
echo "=== TIPPSS SafeGuard-PQ Dashboard ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed. Install Python 3.10+ first."
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "[1/3] Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "[2/3] Installing dashboard dependencies..."
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Launch
echo "[3/3] Starting dashboard..."
echo ""
echo "The dashboard will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop."
echo "----------------------------------------"
streamlit run dashboard.py
