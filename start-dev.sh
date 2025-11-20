#!/bin/bash

# Start development servers for SAM 3D Objects Web App

echo "Starting SAM 3D Objects Web Application..."
echo "=========================================="

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

# Use python3 if available, otherwise use python
PYTHON_CMD=$(command -v python3 || command -v python)

# Check if backend dependencies are installed
if [ ! -d "backend/__pycache__" ] && [ ! -f "backend/.installed" ]; then
    echo "Installing backend dependencies..."
    cd backend
    pip install -r requirements.txt
    touch .installed
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start backend server in background
echo ""
echo "Starting backend server on http://localhost:8000..."
cd backend
$PYTHON_CMD main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend server
echo "Starting frontend server on http://localhost:5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "Web application is running!"
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=========================================="

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
