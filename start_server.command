#!/bin/bash
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Installing dependencies in virtual environment..."
pip install -r requirements.txt

echo "Starting Backend Server at http://localhost:3000..."
echo "Please open your browser and go to: http://localhost:3000"

python server.py
