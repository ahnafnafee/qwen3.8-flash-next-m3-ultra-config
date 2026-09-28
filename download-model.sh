#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/model-service.sh"
command -v hf >/dev/null || { printf 'Install hf first; see README.md.\n' >&2; exit 1; }
# No include/exclude filters: the n-gram sidecar and MTP tensors are required.
exec hf download "$MODEL_REPO" --revision "$MODEL_REVISION" --local-dir "$MODEL_SERVICE_DIR" "$@"
