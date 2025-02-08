#!/bin/bash

start_screen() {
    SCREEN_NAME=$1
    COMMAND=$2
    screen -dmS "$SCREEN_NAME" bash -c "source .venv/bin/activate && exec $COMMAND"
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
        start_screen "dwd" "python -u start.py --instance FetchTemp 2>&1 | tee -a fetching.log"
        start_screen "temps" "python -u start.py 2>&1 | tee -a hometemp.log"
        ;;
    basetemp)
        start_screen "base" "python -u start.py 2>&1 | tee -a basetemp.log"
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 {hometemp|basetemp}"
        exit 1
        ;;
esac