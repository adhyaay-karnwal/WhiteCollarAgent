#!/usr/bin/env bash

# Exit immediately if a command fails (prevents running python if docker fails)
set -e

# --- CONFIGURATION ---
VM_DIR="./core/gui"
PYTHON_CMD="python -m core.main"

# IMPORTANT: Ensure this matches your docker-compose ports
READY_PORT=3000
READY_HOST="localhost"
MAX_WAIT_SECONDS=60
# ---------------------

# --- CLEANUP FUNCTION ---
# This runs ONLY at the very end of the script (on EXIT).
function cleanup {
    echo -e "\n\n--- Cleanup Initiated ---"
    # If we are here, Python has already finished.

    # Stop Docker containers
    echo "[*] Stopping Docker VM containers..."
    # We use '|| true' so the script doesn't fail if docker is already down
    # We use subshell ( ) so we don't change the main script's directory
    (cd "$VM_DIR" && docker compose down) || true

    echo "Shutdown complete."
    # Restore terminal behavior just in case python left it weird
    stty sane 2>/dev/null
}

# --- TRAPS ---

# 1. Handle standard Exit
# Register the cleanup function to run whenever the script ends for any reason.
trap cleanup EXIT

# 2. Handle Ctrl+C (SIGINT)
# We want the Bash script to completely IGNORE Ctrl+C.
# Your Python app should handle Ctrl+C internally (by ignoring it or showing a toast).
trap '' SIGINT


echo "--- Starting Launch Sequence ---"

# 1. Start the Docker VM
echo "[1/3] Launching VM Docker containers in background..."
# Using set -e above handles failures here automatically
(cd "$VM_DIR" && docker compose up -d)

# 2. The Wait Loop
echo "[2/3] Waiting for VM service to be ready on port $READY_PORT..."
waited=0
# We temporarily turn off set -e because the connection check *will* fail initially
set +e
until (echo > /dev/tcp/$READY_HOST/$READY_PORT) 2>/dev/null; do
    if [ $waited -ge $MAX_WAIT_SECONDS ]; then
        echo -e "\n[ERROR] Timed out waiting for VM port $READY_PORT."
        # Exiting here triggers the EXIT trap and stops Docker automatically
        exit 1
    fi
    echo -n "." ; sleep 1
    waited=$((waited + 1))
done
# Turn set -e back on
set -e
echo -e "\n[OK] VM Service is reachable!"


# 3. Start the Python Agent
echo "[3/3] Launching Python Agent..."
echo "--------------------------------"
echo "Type '/exit' or use your defined quit hotkey (e.g., Ctrl+Q) to stop."
echo "Ctrl+C handled by app logic."
echo "--------------------------------"

# Run Python in the FOREGROUND.
# The script blocks here until Python exits.
# It has full control of terminal input.
$PYTHON_CMD

# When Python exits normally, the script continues here.
echo -e "\n[i] Agent exited normally."

# The script hits end-of-file here.
# The 'trap cleanup EXIT' fires automatically.
# Docker is stopped.