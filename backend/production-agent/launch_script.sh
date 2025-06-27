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
if [ ! -f "production_mindbot.py" ]; then
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

# Check environment variables
print_info "Validating environment variables..."
REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_SERVICE_ROLE_KEY" "LIVEKIT_API_KEY" "LIVEKIT_API_SECRET" "LIVEKIT_URL" "OPENAI_API_KEY" "DEEPGRAM_API_KEY" "STRIPE_SECRET_KEY")

missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    print_status "All required environment variables are set"
else
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    print_warning "Please set these variables in your .env file"
    exit 1
fi

# Test connections
print_info "Testing external service connections..."

# Test Supabase connection
print_info "Testing Supabase connection..."
python3 -c "
import os
from supabase_client import supabase_client
try:
    response = supabase_client.supabase.table('pricing_tiers').select('count', count='exact').execute()
    print('✅ Supabase connection successful')
except Exception as e:
    print(f'❌ Supabase connection failed: {e}')
    exit(1)
" || exit 1

# Test Stripe connection
print_info "Testing Stripe connection..."
python3 -c "
import stripe
import os
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
try:
    stripe.Account.retrieve()
    print('✅ Stripe connection successful')
except Exception as e:
    print(f'❌ Stripe connection failed: {e}')
    exit(1)
" || exit 1

# Test OpenAI connection
print_info "Testing OpenAI connection..."
python3 -c "
import openai
import os
openai.api_key = os.getenv('OPENAI_API_KEY')
try:
    # Just validate the key format
    key = os.getenv('OPENAI_API_KEY', '')
    if key.startswith('sk-'):
        print('✅ OpenAI API key format valid')
    else:
        print('❌ OpenAI API key format invalid')
        exit(1)
except Exception as e:
    print(f'❌ OpenAI validation failed: {e}')
    exit(1)
" || exit 1

print_status "All external service connections validated"

# Create log directory
mkdir -p logs
print_status "Log directory created"

# Function to start service in background
start_service() {
    local service_name=$1
    local command=$2
    local log_file="logs/${service_name}.log"
    
    print_info "Starting $service_name..."
    
    # Start service in background and redirect output to log file
    nohup $command > "$log_file" 2>&1 &
    local pid=$!
    
    # Store PID for later cleanup
    echo $pid > "logs/${service_name}.pid"
    
    # Wait a moment and check if process is still running
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        print_status "$service_name started (PID: $pid)"
        echo "  Log file: $log_file"
    else
        print_error "$service_name failed to start"
        print_error "Check log file: $log_file"
        return 1
    fi
}

# Start payment webhook server first
print_info "Starting payment webhook server..."
start_service "webhook-server" "python payment_webhook_server.py"

# Wait for webhook server to be ready
print_info "Waiting for webhook server to be ready..."
sleep 5

# Test webhook server
if curl -f -s http://localhost:8003/health > /dev/null; then
    print_status "Webhook server is ready"
else
    print_error "Webhook server health check failed"
    exit 1
fi

# Start the main voice agent
print_info "Starting MindBot voice agent..."

# Determine the command based on arguments
if [ "$1" = "dev" ]; then
    print_info "Starting in development mode..."
    python production_mindbot.py dev
elif [ "$1" = "start" ]; then
    print_info "Starting in production mode..."
    start_service "voice-agent" "python production_mindbot.py start"
    
    # Monitor the voice agent
    print_info "Voice agent started successfully!"
    print_info "Monitoring services... (Press Ctrl+C to stop all services)"
    
    # Function to cleanup on exit
    cleanup() {
        print_info "Stopping all services..."
        
        # Stop services by PID
        for pid_file in logs/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                local service_name=$(basename "$pid_file" .pid)
                
                if kill -0 $pid 2>/dev/null; then
                    print_info "Stopping $service_name (PID: $pid)..."
                    kill $pid
                    
                    # Wait for graceful shutdown
                    for i in {1..10}; do
                        if ! kill -0 $pid 2>/dev/null; then
                            break
                        fi
                        sleep 1
                    done
                    
                    # Force kill if still running
                    if kill -0 $pid 2>/dev/null; then
                        kill -9 $pid
                    fi
                fi
                
                rm -f "$pid_file"
            fi
        done
        
        print_status "All services stopped"
    }
    
    # Set trap for cleanup
    trap cleanup EXIT INT TERM
    
    # Monitor services
    while true; do
        # Check if any service died
        for pid_file in logs/*.pid; do
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                local service_name=$(basename "$pid_file" .pid)
                
                if ! kill -0 $pid 2>/dev/null; then
                    print_error "$service_name died (PID: $pid)"
                    print_error "Check log file: logs/${service_name}.log"
                    exit 1
                fi
            fi
        done
        
        sleep 10
    done
else
    print_info "Starting in interactive mode..."
    print_warning "Use 'python production_mindbot.py start' for production or 'python production_mindbot.py dev' for development"
    python production_mindbot.py start
fi