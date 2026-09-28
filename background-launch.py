#!/usr/bin/env python3
"""Detach the server from the calling terminal and its process group."""
import datetime
import os
from pathlib import Path
import subprocess
import sys


def main():
    launcher, log_path = map(Path, sys.argv[1:])
    os.umask(0o077)
    with log_path.open("ab", buffering=0) as log:
        log.write(f"\n--- Start {datetime.datetime.now().astimezone().isoformat()} ---\n".encode())
        process = subprocess.Popen(
            [str(launcher)],
            cwd=str(launcher.parent),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    print(process.pid)


if __name__ == "__main__":
    main()
