#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/model-service.sh"

if ! model_pid="$(model_find_pid)"; then
    printf 'Stopped. Start with macqwen start.\n'
    exit 3
fi
status_code=0
if curl --silent --fail --connect-timeout 1 --max-time 2 "http://127.0.0.1:$MODEL_SERVICE_PORT/health" >/dev/null 2>&1; then
    printf 'Running and healthy (PID %s).\n' "$model_pid"
else
    printf 'Process running; HTTP service is not ready (PID %s).\n' "$model_pid"
    status_code=2
fi
lsof -nP -a -p "$model_pid" -iTCP:"$MODEL_SERVICE_PORT" -sTCP:LISTEN 2>/dev/null || true
model_print_urls
exit "$status_code"
