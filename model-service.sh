#!/bin/bash
# Shared by the repo scripts and the installed copies; never stores credentials.
MODEL_SERVICE_SCRIPTS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$MODEL_SERVICE_SCRIPTS_DIR/model.lock.sh"
MODEL_SERVICE_DIR="${QWEN_MODEL_DIR:-$HOME/Documents/Models/$MODEL_DIRECTORY_NAME}"
case "$MODEL_SERVICE_DIR" in
    /*) ;;
    *) printf 'QWEN_MODEL_DIR must be an absolute path.\n' >&2; exit 1 ;;
esac
export QWEN_MODEL_DIR="$MODEL_SERVICE_DIR"
MODEL_SERVICE_STATE="$MODEL_SERVICE_DIR/.service"
MODEL_SERVICE_PID_FILE="$MODEL_SERVICE_STATE/server.pid"
MODEL_SERVICE_LOG="$MODEL_SERVICE_STATE/console.log"
MODEL_SERVICE_LAUNCHER="$MODEL_SERVICE_SCRIPTS_DIR/serve_mlx_best.sh"
MODEL_SERVICE_PORT="${QWEN_PORT:-11234}"
MODEL_SERVICE_HOST="${QWEN_HOST:-0.0.0.0}"

model_pid_matches() {
    local candidate="$1" command_text
    case "$candidate" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "$candidate" 2>/dev/null || return 1
    command_text="$(ps -p "$candidate" -o command= 2>/dev/null)" || return 1
    case "$command_text" in
        *mlx-serve*"--model $MODEL_SERVICE_DIR "*) return 0 ;;
        *) return 1 ;;
    esac
}

model_find_pid() {
    local candidate
    if [[ -r "$MODEL_SERVICE_PID_FILE" ]]; then
        read -r candidate < "$MODEL_SERVICE_PID_FILE" || candidate=""
        if model_pid_matches "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    fi
    # Adopt an already-running instance only if its exact checkpoint matches.
    for candidate in $(lsof -nP -tiTCP:"$MODEL_SERVICE_PORT" -sTCP:LISTEN 2>/dev/null); do
        if model_pid_matches "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

model_print_urls() {
    local tailnet_ip=""
    printf 'Local UI: http://127.0.0.1:%s\n' "$MODEL_SERVICE_PORT"
    if command -v tailscale >/dev/null 2>&1; then
        tailnet_ip="$(tailscale ip -4 2>/dev/null)" || tailnet_ip=""
    fi
    if [[ -n "$tailnet_ip" ]]; then
        printf 'Tailnet API (requires a reachable binding): http://%s:%s/v1\n' "$tailnet_ip" "$MODEL_SERVICE_PORT"
    fi
    printf 'Model ID: %s\n' "$(basename -- "$MODEL_SERVICE_DIR")"
    printf 'Console log: %s\n' "$MODEL_SERVICE_LOG"
}
