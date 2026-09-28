#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/model-service.sh"

if ! model_pid="$(model_find_pid)"; then
    printf 'This Qwen model is already stopped.\n'
    exit 0
fi
printf 'Stopping Qwen (PID %s)...\n' "$model_pid"
kill -TERM "$model_pid"
for ((attempt=0; attempt<60; attempt++)); do
    if ! model_pid_matches "$model_pid"; then
        if [[ -r "$MODEL_SERVICE_PID_FILE" ]]; then
            read -r recorded_pid < "$MODEL_SERVICE_PID_FILE" || recorded_pid=""
            [[ "$recorded_pid" != "$model_pid" ]] || rm -f "$MODEL_SERVICE_PID_FILE"
        fi
        printf 'Stopped.\n'
        exit 0
    fi
    sleep 1
done
printf 'PID %s is still shutting down; no force kill was sent. Inspect %s.\n' "$model_pid" "$MODEL_SERVICE_LOG" >&2
exit 1
