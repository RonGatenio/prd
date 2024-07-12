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
  exec "$@"
else
  # If no command is provided, fall back to an interactive bash shell
  exec /bin/bash
fi
