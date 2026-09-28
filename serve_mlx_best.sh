#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/model-service.sh"

mlx_binary="${MLX_SERVE_BIN:-$(command -v mlx-serve || true)}"
if [[ -z "$mlx_binary" || ! -x "$mlx_binary" ]]; then
    printf 'mlx-serve not found. Install the runtime as described in README.md.\n' >&2
    exit 1
fi
if [[ ! -s "$MODEL_SERVICE_DIR/config.json" || ! -s "$MODEL_SERVICE_DIR/ngram_table.bin" ]]; then
    printf 'Model is missing or incomplete at %s; run download-model.sh and verify-model.sh.\n' "$MODEL_SERVICE_DIR" >&2
    exit 1
fi

exec "$mlx_binary" \
    --model "$MODEL_SERVICE_DIR" \
    --serve \
    --host "$MODEL_SERVICE_HOST" \
    --port "$MODEL_SERVICE_PORT" \
    --ctx-size "${QWEN_CONTEXT_SIZE:-262144}" \
    --timeout 0 \
    --no-vision \
    --kv-quant 8 \
    --kv-attn-mode fused \
    --mtp \
    --mtp-depth "${QWEN_MTP_DEPTH:-3}" \
    --no-pld \
    --prefix-cache-mem "${QWEN_PREFIX_CACHE_MEM:-16GB}" \
    --prefix-cache-entries 2 \
    --metrics
