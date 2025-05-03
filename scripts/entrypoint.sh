#!/bin/bash

# Function to handle termination signals
_term() {
  echo "Caught SIGTERM signal!"
  exec /bin/bash
}

# Trap termination signals
trap _term SIGTERM SIGINT

# Get the scripts dir path
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup env
. $SCRIPTS_DIR/setup-env.sh

# Execute the command passed as arguments, if any
if [ "$#" -gt 0 ]; then

  # Start the child process in the foreground
  "$@" &

  # Get the PID of the child process
  child_pid=$!

  # Wait for the child process to exit
  wait $child_pid

  # Open an interactive shell
  exec /bin/bash

else
  
  # If no command is provided, fall back to an interactive bash shell
  exec /bin/bash

fi
