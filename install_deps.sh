#!/bin/bash
# Installation script for multi-agent support system dependencies

echo "Installing dependencies for multi-agent support system..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing packages from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "Installation complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"

