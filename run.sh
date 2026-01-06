#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- CONFIGURATION ---
# Define paths relative to where this script is run
VM_DIR="./core/gui"
PYTHON_CMD="python -m core.main"

# IMPORTANT: Change this port to whatever service indicates your VM is ready.
# e.g., 22 for SSH, 80 for web, 5432 for Postgres, etc.
READY_PORT=3000
READY_HOST="localhost"
MAX_WAIT_SECONDS=60
# ---------------------

# Helper function for cleanup on Ctrl+C
function cleanup {
    echo -e "\n\n[!] Stopping script."
    echo "If you want to stop the Docker VM as well, run:"
    echo "cd $VM_DIR && docker compose down"
    # Optional: Uncomment next line to auto-stop docker on Ctrl+C
    # (cd "$VM_DIR" && docker compose down)
}
# Register the cleanup function for SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "--- Starting Launch Sequence ---"

# 1. Start the Docker VM
echo "[1/3] Launching VM Docker containers..."
# We use subshell ( ) so we don't actually change the script's working directory
(cd "$VM_DIR" && docker compose up -d)
echo "Docker containers started."


# 2. The Wait Loop
echo "[2/3] Waiting for VM service to be ready on port $READY_PORT..."

waited=0
# This loop tries to open a TCP connection to the host/port.
# It works in pure bash without needing 'nc' or 'telnet' installed.
until (echo > /dev/tcp/$READY_HOST/$READY_PORT) 2>/dev/null; do
    if [ $waited -ge $MAX_WAIT_SECONDS ]; then
        echo -e "\n[ERROR] Timed out waiting for VM port $READY_PORT after $MAX_WAIT_SECONDS seconds."
        echo "Please check docker logs."
        exit 1
    fi
    
    echo -n "." ; sleep 1
    waited=$((waited + 1))
done

echo -e "\n[OK] VM Service is reachable!"


# 3. Start the Python Agent
echo "[3/3] Launching Python Agent..."
echo "Running: $PYTHON_CMD"
echo "--------------------------------"

# Run the python command. Since it's not backgrounded (&), 
# this script will block here until the python agent exits.
$PYTHON_CMD