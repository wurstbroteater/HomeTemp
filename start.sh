#!/bin/bash

start_screen() {
    SCREEN_NAME=$1
    COMMAND=$2
    screen -dmS "$SCREEN_NAME" bash -c "source .venv/bin/activate && exec $COMMAND"
    echo "Started screen '$SCREEN_NAME' running: $COMMAND"
}

start_grafana() {
    local compose_file="./monitoring/docker-compose.yml"
    echo "---------- Starting Grafana Fronted ----------"
    # Validate that path is absolute or relative and that the file exists
    if [ ! -f "$compose_file" ]; then
        echo "[Grafana] Error: Frontend docker-compose file not found at $compose_file"
        return 1
    fi

    local project_dir
    project_dir=$(dirname "$compose_file")
    local project_name
    project_name=$(basename "$project_dir" | tr -cd '[:alnum:]')

    echo "[Grafana] Checking services in $compose_file..."

    local running_services
    running_services=$(docker compose -f "$compose_file" ps --services --filter "status=running")

    if [ -n "$running_services" ]; then
        echo "[Grafana] Services already running:"
        echo "$running_services"
    else
        echo "[Grafana] Starting services from $compose_file ..."
        docker compose -f "$compose_file" up -d
    fi

    echo "[Grafana] Sleeping 5s to give frontend some time to start"
    sleep 5
    echo "[Grafana] initialization done!"
}

start_motioneye() {
    local compose_file="./motioneye/docker-compose.yml"
    echo "---------- Starting MotionEye Fronted ----------"
    # Validate that path is absolute or relative and that the file exists
    if [ ! -f "$compose_file" ]; then
        echo "[MotionEye] Error: Frontend docker-compose file not found at $compose_file"
        return 1
    fi

    local project_dir
    project_dir=$(dirname "$compose_file")
    local project_name
    project_name=$(basename "$project_dir" | tr -cd '[:alnum:]')

    echo "[MotionEye] Checking services in $compose_file..."

    local running_services
    running_services=$(docker compose -f "$compose_file" ps --services --filter "status=running")

    if [ -n "$running_services" ]; then
        echo "[MotionEye] Services already running:"
        echo "$running_services"
    else
        echo "[MotionEye] Starting services from $compose_file ..."
        docker compose -f "$compose_file" up -d
    fi

    echo "[MotionEye] Sleeping 5s to give frontend some time to start"
    sleep 5
    echo "[MotionEye] initialization done!"
}

#################################################################################################################

# Check if correct argument was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 {hometemp|basetemp}"
    exit 1
fi

# Requires screen command to be installed!
# starts detached screens for hometemp or basetemp
case "$1" in
    hometemp)
        start_grafana
        start_screen "dwd" "python -u start.py --port 8001 --instance FetchTemp 2>&1 | tee -a fetching.log"
        start_screen "temps" "python -u start.py --port 8002 2>&1 | tee -a hometemp.log"
        ;;
    basetemp)
        start_grafana
        start_motioneye
        start_screen "base" "python -u start.py --port 8003 2>&1 | tee -a basetemp.log"
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 {hometemp|basetemp}"
        exit 1
        ;;
esac