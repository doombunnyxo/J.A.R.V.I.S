#!/bin/bash

# Discord Bot Startup Script
# This script sets up the virtual environment, installs dependencies, and starts the bot

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[$(date)] Starting Discord Bot setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date)]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date)]${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date)]${NC} �  $1"
}

print_error() {
    echo -e "${RED}[$(date)]${NC} L $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_status "Found Python $PYTHON_VERSION"

# Check if we have Python 3.8+
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    print_error "Python 3.8 or higher is required"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source ./venv/bin/activate

if [ $? -eq 0 ]; then
    print_success "Virtual environment activated"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
print_status "Upgrading pip..."
python -m pip install --upgrade pip > /dev/null 2>&1

# Install/update requirements
if [ -f "requirements.txt" ]; then
    print_status "Installing/updating dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_warning "requirements.txt not found, skipping dependency installation"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found - bot may not start without proper configuration"
    print_status "Create a .env file with your Discord token and API keys"
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    print_error "main.py not found in current directory"
    exit 1
fi

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    print_status "Creating data directory..."
    mkdir -p data
    print_success "Data directory created"
fi

# Set proper permissions for data directory
chmod 755 data

print_success "Setup completed successfully!"
print_status "Starting Discord Bot..."

# Start the bot
exec python main.py