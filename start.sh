#!/bin/bash

# make relative path work for script execution from any location
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
CONFIG_FILE="$PWD/config.ini"


start_database() {
    echo "---------- Starting database container ----------"

    # Read the database configuration using Python's ConfigParser.
    # NUL-separated values preserve spaces and special characters.
    local -a values=()

    mapfile -d '' -t values < <(python3 - "$CONFIG_FILE" <<'PY'
import configparser
import sys

config = configparser.ConfigParser()

if not config.read(sys.argv[1]):
    sys.exit(f"Cannot read config file: {sys.argv[1]}")

db = config["db"] if config.has_section("db") else None

enabled = (db.getboolean("enabled", fallback=True) if db is not None else False)

values = [
    "true" if enabled else "false",
    db.get("container_name", fallback="").strip() if db else "",
    db.get("db_port", fallback="").strip() if db else "",
    db.get("db_user", fallback="").strip() if db else "",
    db.get("db_name", fallback="").strip() if db else "",
    db.get("db_pw", fallback="") if db else "",
]

sys.stdout.buffer.write(b"\0".join(value.encode() for value in values) + b"\0")
PY
    )

    if (( ${#values[@]} != 6 )); then
        echo "[Postgres] Failed to read database configuration." >&2
        return 1
    fi

    local enabled="${values[0]}"
    local container_name="${values[1]}"
    local db_port="${values[2]}"
    local db_user="${values[3]}"
    local db_name="${values[4]}"
    local db_pw="${values[5]}"

    # Database disabled or [db] section missing.
    if [[ "$enabled" != "true" ]]; then
        echo "[Postgres] Database disabled. Skipping."
        return 0
    fi

    # Database enabled but no container name provided.
    if [[ -z "$container_name" ]]; then
        echo "[Postgres] No container_name configured."
        return 1
    fi

    # Validate configuration before accessing Docker.
    if [[ -z "$db_user" || -z "$db_name" || -z "$db_pw" ||
          ! "$db_port" =~ ^[0-9]+$ ]] ||
       (( 10#$db_port < 1 || 10#$db_port > 65535 )); then
        echo "[Postgres] Missing or invalid DB configuration." >&2
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        echo "[Postgres] Docker daemon unavailable." >&2
        return 1
    fi

    # Reuse an existing container when possible.
    if docker container inspect "$container_name" >/dev/null 2>&1; then

        if [[ "$(docker inspect -f '{{.State.Running}}' "$container_name")" == "true" ]]; then
            echo "[Postgres] Container '$container_name' already running."
        else
            echo "[Postgres] Starting existing container '$container_name'..."

            if ! docker start "$container_name" >/dev/null; then
                echo "[Postgres] Failed to start container." >&2
                return 1
            fi
        fi

    else
        echo "[Postgres] Creating container '$container_name'..."

        # Export variables without exposing passwords in CLI arguments.
        local POSTGRES_USER="$db_user"
        local POSTGRES_PASSWORD="$db_pw"
        local POSTGRES_DB="$db_name"

        export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB

        if ! docker run -d \
            --name "$container_name" \
            -e POSTGRES_USER \
            -e POSTGRES_PASSWORD \
            -e POSTGRES_DB \
            -p "${db_port}:5432" \
            -v "${container_name}-data:/var/lib/postgresql/data" \
            postgres:16 >/dev/null; then

            echo "[Postgres] Container creation failed." >&2
            return 1
        fi
    fi

    # Wait until PostgreSQL accepts authenticated queries.
    echo "[Postgres] Container started successfully."
    return 0
}


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
        start_database || exit 1
        start_grafana
        start_screen "dwd" "python -u start.py --port 8001 --instance FetchTemp 2>&1 | tee -a fetching.log"
        start_screen "temps" "python -u start.py --port 8002 2>&1 | tee -a hometemp.log"
        ;;
    basetemp)
        start_database || exit 1
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