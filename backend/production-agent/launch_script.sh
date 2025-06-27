#!/bin/bash
# MindBot Production Launch Script
# Launches all components for the production voice agent system

set -e  # Exit on any error

echo "🚀 MindBot Production Launch Script"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check if running from correct directory
if [ ! -f "main.py" ]; then
    print_error "Please run this script from the backend/production-agent directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
if python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    print_status "Python $PYTHON_VERSION is supported"
else
    print_error "Python 3.11+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Install/update requirements
print_info "Installing/updating requirements..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Requirements installed"

# Create log directory
mkdir -p logs
print_status "Log directory created"

print_info "Starting MindBot system..."
python main.py