#!/usr/bin/env python3
"""Install management scripts only. Never downloads, removes, or edits weights."""
import argparse
import datetime
from pathlib import Path
import shlex
import shutil

MODEL_NAME = "ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit"
FILES = (
    "model.lock.sh", "model-service.sh", "serve_mlx_best.sh", "start.sh",
    "stop.sh", "status.sh", "background-launch.py", "download-model.sh",
    "verify-model.sh",
)


def wrapper(model_dir, target):
    return (
        '#!/bin/bash\n# Managed by qwen3.8-flash-next-m3-ultra-config.\n'
        'if [[ -z "${QWEN_MODEL_DIR:-}" ]]; then\n'
        f'    export QWEN_MODEL_DIR={shlex.quote(str(model_dir))}\n'
        'fi\n'
        f'exec {shlex.quote(str(target))} "$@"\n'
    ).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path.home() / "Documents/Models" / MODEL_NAME)
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    parser.add_argument("--force", action="store_true", help="Back up and replace differing management scripts")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    model_dir = args.model_dir.expanduser().resolve()
    bin_dir = args.bin_dir.expanduser().resolve()
    installed = model_dir / ".qwen-config"
    payloads = {installed / name: (source / name).read_bytes() for name in FILES}
    for command in ("start", "stop", "status"):
        payloads[model_dir / f"{command}.sh"] = wrapper(model_dir, installed / f"{command}.sh")
        payloads[bin_dir / f"qwen-{command}"] = wrapper(model_dir, installed / f"{command}.sh")
    conflicts = [p for p, data in payloads.items() if p.exists() and (not p.is_file() or p.read_bytes() != data)]
    symlinks = [p for p in payloads if p.is_symlink()]
    if symlinks:
        parser.error("Refusing symlink destinations: " + ", ".join(map(str, symlinks)))
    if any(p.exists() and not p.is_file() for p in payloads):
        parser.error("A target script path is not a regular file")
    if conflicts and not args.force:
        parser.error("Existing scripts differ; review then rerun with --force to back them up: " + ", ".join(map(str, conflicts)))
    if conflicts:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = model_dir / ".qwen-config-backups" / stamp
        backup.mkdir(parents=True, mode=0o700)
        for number, path in enumerate(conflicts):
            shutil.copy2(path, backup / f"{number:02d}-{path.name}")
        print(f"Previous management scripts backed up to {backup}")
    for path, data in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755)
    print(f"Installed scripts under {installed}")
    print(f"Commands: {bin_dir}/qwen-start, qwen-stop, qwen-status")
    print(f"Ensure {bin_dir} is on PATH. Model weights were not changed; server was not restarted.")


if __name__ == "__main__":
    main()
