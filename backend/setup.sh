#!/bin/bash
# Setup script for HIM backend

echo "Setting up HIM backend..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your database URL and secret key!"
fi

# Create temp directory
mkdir -p /tmp/him_videos

echo "Setup complete!"
echo "Don't forget to:"
echo "1. Edit .env with your database URL and secret key"
echo "2. Set up PostgreSQL database"
echo "3. Run: uvicorn main:app --reload"
