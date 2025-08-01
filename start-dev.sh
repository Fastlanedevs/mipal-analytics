#!/bin/bash

# MIPAL Analytics - Development Server Startup Script
# This script starts all services concurrently for local development

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[MIPAL]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        print_warning "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 2
    fi
}

# Function to cleanup background processes on script exit
cleanup() {
    print_status "Shutting down services..."
    # Kill all background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

print_status "Starting MIPAL Analytics Development Environment"
echo

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists uv; then
    print_error "uv is not installed. Please install it first: https://docs.astral.sh/uv/"
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/package.json" ]; then
    print_error "This script must be run from the mipal-analytics root directory"
    exit 1
fi

# Check for .env file in backend
if [ ! -f "backend/.env" ]; then
    print_error "backend/.env file not found. Please create it with required environment variables."
    exit 1
fi

# Check for .env.local file in frontend
if [ ! -f "frontend/.env.local" ]; then
    print_warning "frontend/.env.local file not found. Using default configuration."
fi

# Check and kill processes on required ports
print_status "Checking ports..."
BACKEND_PORT=8000
FRONTEND_PORT=3000
WORKER_PORT=8001
CODEX_PORT=8002

if port_in_use $BACKEND_PORT; then
    print_warning "Port $BACKEND_PORT is in use"
    kill_port $BACKEND_PORT
fi

if port_in_use $FRONTEND_PORT; then
    print_warning "Port $FRONTEND_PORT is in use"
    kill_port $FRONTEND_PORT
fi

if port_in_use $WORKER_PORT; then
    print_warning "Port $WORKER_PORT is in use"
    kill_port $WORKER_PORT
fi

if port_in_use $CODEX_PORT; then
    print_warning "Port $CODEX_PORT is in use"
    kill_port $CODEX_PORT
fi

echo

# Install dependencies if needed
print_status "Checking dependencies..."

# Check backend dependencies
cd backend
if [ ! -d ".venv" ] || [ ! -f ".venv/pyvenv.cfg" ]; then
    print_status "Installing backend dependencies..."
    uv venv
    uv pip install -e . --all-extras
fi
cd ..

# Check frontend dependencies
cd frontend
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install
fi
cd ..

echo

# Start services
print_status "Starting services..."

# Start Backend API Server
print_status "Starting Backend API Server (Port: $BACKEND_PORT)..."
cd backend
uv run --env-file .env python3 cmd_server/server/main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start Worker Service
print_status "Starting Worker Service..."
cd backend
uv run --env-file .env python3 cmd_server/worker/main.py &
WORKER_PID=$!
cd ..

# Start Code Execution Server
print_status "Starting Code Execution Server (Port: $CODEX_PORT)..."
cd backend
uv run --env-file .env python3 cmd_server/code_execution_server/main.py &
CODEX_PID=$!
cd ..

# Start Frontend Development Server
print_status "Starting Frontend Development Server (Port: $FRONTEND_PORT)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for services to start
sleep 5

echo
print_status "All services started successfully!"
echo
echo -e "${CYAN}🚀 MIPAL Analytics Development Environment${NC}"
echo -e "${CYAN}=========================================${NC}"
echo -e "📱 Frontend:              ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "🔧 Backend API:           ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "📚 API Documentation:     ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "⚡ Code Execution Server: ${GREEN}http://localhost:$CODEX_PORT${NC}"
echo -e "🔍 Worker Service:        ${GREEN}Running in background${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo

# Function to check service health
check_services() {
    local all_running=true
    
    # Check if processes are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend API Server stopped unexpectedly"
        all_running=false
    fi
    
    if ! kill -0 $WORKER_PID 2>/dev/null; then
        print_error "Worker Service stopped unexpectedly"
        all_running=false
    fi
    
    if ! kill -0 $CODEX_PID 2>/dev/null; then
        print_error "Code Execution Server stopped unexpectedly"
        all_running=false
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend Development Server stopped unexpectedly"
        all_running=false
    fi
    
    if [ "$all_running" = false ]; then
        print_error "Some services have stopped. Exiting..."
        cleanup
    fi
}

# Monitor services
while true; do
    sleep 10
    check_services
done