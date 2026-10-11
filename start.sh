#!/usr/bin/env bash

# Resolve project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo " Starting Email Routing System"
echo "=================================================="

# Function to clean up child processes on Ctrl+C / exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "All servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start FastAPI Backend
echo "Starting FastAPI backend on http://localhost:8000 ..."
"$SCRIPT_DIR/venv/bin/uvicorn" backend.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Wait 1 second for backend to bind port
sleep 1

# 2. Start Vite Frontend
echo "Starting Vite React frontend on http://localhost:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

cd "$SCRIPT_DIR"

echo ""
echo "=================================================="
echo " Both servers are running!"
echo " - Frontend: http://localhost:5173"
echo " - Backend:  http://localhost:8000"
echo " Press [Ctrl+C] to stop both servers."
echo "=================================================="
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
