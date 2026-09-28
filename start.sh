#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/model-service.sh"

if model_pid="$(model_find_pid)"; then
    printf 'Already running (PID %s).\n' "$model_pid"
    exec "$MODEL_SERVICE_SCRIPTS_DIR/status.sh"
fi
port_owner="$(lsof -nP -tiTCP:"$MODEL_SERVICE_PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "$port_owner" ]]; then
    printf 'Cannot start: port %s belongs to another process (PID %s).\n' "$MODEL_SERVICE_PORT" "$port_owner" >&2
    exit 1
fi
if [[ ! -s "$MODEL_SERVICE_DIR/config.json" || ! -s "$MODEL_SERVICE_DIR/ngram_table.bin" ]]; then
    printf 'Download and verify the model first: %s\n' "$MODEL_SERVICE_DIR" >&2
    exit 1
fi
umask 077
mkdir -p "$MODEL_SERVICE_STATE"
model_pid="$(python3 "$MODEL_SERVICE_SCRIPTS_DIR/background-launch.py" "$MODEL_SERVICE_LAUNCHER" "$MODEL_SERVICE_LOG")"
printf '%s\n' "$model_pid" > "$MODEL_SERVICE_PID_FILE"
printf 'Starting Qwen (PID %s); loading the model may take a moment.\n' "$model_pid"
for ((attempt=0; attempt<120; attempt++)); do
    if ! kill -0 "$model_pid" 2>/dev/null; then
        printf 'Server exited during startup. Recent log:\n' >&2
        tail -n 30 "$MODEL_SERVICE_LOG" >&2
        rm -f "$MODEL_SERVICE_PID_FILE"
        exit 1
    fi
    if model_pid_matches "$model_pid" && curl --silent --fail --connect-timeout 1 --max-time 1 "http://127.0.0.1:$MODEL_SERVICE_PORT/health" >/dev/null 2>&1; then
        printf 'Ready; configured binding %s:%s.\n' "$MODEL_SERVICE_HOST" "$MODEL_SERVICE_PORT"
        model_print_urls
        exit 0
    fi
    sleep 1
done
printf 'Still starting; run qwen-status or inspect %s.\n' "$MODEL_SERVICE_LOG" >&2
exit 2
