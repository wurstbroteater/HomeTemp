#!/bin/bash

start_screen() {
    SCREEN_NAME=$1
    COMMAND=$2
    screen -dmS "$SCREEN_NAME" bash -c "source .venv/bin/activate && $COMMAND"
    echo "Started screen '$SCREEN_NAME' running: $COMMAND"
}

# Check if correct argument was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 {hometemp|basetemp}"
    exit 1
fi

# Requires screen command to be installed!
# starts detached screens for hometemp or basetemp
case "$1" in
    hometemp)
        start_screen "temps" "python start.py"
        start_screen "dwd" "python fetch_forecasts.py"
        ;;
    basetemp)
        start_screen "base" "python start.py"
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 {hometemp|basetemp}"
        exit 1
        ;;
esac
