# Qwen3.8 Flash Next: reproducible Apple Silicon configuration

Portable scripts for the **ARC4NUM uncensored MLX-Serve 4-bit checkpoint**, with a
native **262,144-token total window**, MTP depth 3, fused 8-bit KV, and a 16 GB
prefix cache. Model weights, credentials, caches, and logs are not in this repo.

Tested September 28, 2026 on a **Mac Studio M3 Ultra, 80 GPU cores, 256 GiB RAM,
macOS 26.5.2**, using **mlx-serve 26.9.6 / MLX 0.32.2**. Near-full-window synthetic
code tests produced about **98–106 output tok/s**; technical prose was **67.33
tok/s**. Cold long-prompt processing took about 205 seconds. These are measured
workload-specific results, **not an 80 tok/s guarantee** for arbitrary prompts or
other Macs. Full methodology and limitations: [BENCHMARK.md](BENCHMARK.md).

## Set up another Mac

Use Apple Silicon and macOS 26.2+ for this runtime. The checkpoint publisher lists
96 GB as a loading minimum and 128 GB for long contexts; **this configuration was
tested only with 256 GiB**. Allow at least 120 GB free on a fast SSD for the roughly
107 GB model, plus space for the OS and runtime. A smaller-memory Mac may need a
smaller context and prefix cache. No system memory-limit overrides are installed.
See the [model card](https://huggingface.co/ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit)
and [runtime requirements](https://github.com/ddalcu/mlx-serve).

1. Install Homebrew from [brew.sh](https://brew.sh/) if needed, then the tools:

   ```sh
   brew install git gh uv python
   brew tap ddalcu/mlx-serve https://github.com/ddalcu/mlx-serve
   brew install ddalcu/mlx-serve/mlx-serve
   uv tool install 'huggingface_hub==2.0.0'
   export PATH="$HOME/.local/bin:$PATH"
   mlx-serve --version
   ```

   Homebrew installs its current release, which may differ from the measured one.
   For the exact tested runtime, download the arm64 CLI archive from
   [release v26.9.6](https://github.com/ddalcu/mlx-serve/releases/tag/v26.9.6), verify
   its SHA-256 below, extract the entire archive (including companion libraries),
   and set `MLX_SERVE_BIN` to its `mlx-serve` executable. Do not disable Gatekeeper
   or overwrite a working runtime just to downgrade.

   ```text
   mlx-serve-bin-macos-arm64.tar.gz
   SHA-256: bb4ec3f6ee250745a1d04ef685d3f15b734b560f482a65d0e8bacb512e78bacf
   ```

2. Clone this private repo with your own GitHub login:

   ```sh
   gh auth login
   mkdir -p "$HOME/Documents/Models"
   cd "$HOME/Documents/Models"
   gh repo clone ahnafnafee/qwen3.8-flash-next-m3-ultra-config
   cd qwen3.8-flash-next-m3-ultra-config
   ```

3. Download and verify the complete checkpoint:

   ```sh
   # Optional for this public model; use your own login if HF requests it.
   hf auth login
   ./download-model.sh --dry-run
   ./download-model.sh
   ./verify-model.sh
   ```

   Downloads are pinned in [model.lock.sh](model.lock.sh) to revision
   `9ebf9993b1eaec96aec938bf883601b51a90393b`. Default destination:
   `~/Documents/Models/ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit`.
   Keep **every upstream file**, including the 32,000,153,976-byte
   `ngram_table.bin`, all weight shards, tokenizer/config files, and native MTP
   tensors. Rerun the download after an interruption; do not substitute a GGUF
   or a differently formatted MLX checkpoint. Checksum verification scans the
   large files and can take several minutes. It permits our extra local scripts.

   Never paste a token into a script or commit it. `hf auth login` stores the
   credential outside this repository. Model use remains subject to its own
   license; the publisher's uncensored label was not independently evaluated.

4. Install the commands and start:

   ```sh
   python3 install.py
   macqwen start
   macqwen status
   # macqwen stop
   ```

   If `~/.local/bin` is not on your persistent PATH, add
   `export PATH="$HOME/.local/bin:$PATH"` to your shell configuration.
   The installer copies scripts into the model's `.qwen-config/`, adds
   `macqwen`, `start.sh`, `stop.sh`, and `status.sh` in the model directory, and
   creates `macqwen` on PATH. The earlier `qwen-start`, `qwen-stop`, and
   `qwen-status` commands remain as compatibility aliases. The clone can move
   without breaking
   installed commands. No model weights are changed. Differing existing scripts
   are refused unless you pass `--force`, which backs up those scripts first.
   After pulling updates, rerun the installer with `--force`, then stop/start.

## Network access and lifecycle

The default binding is **`0.0.0.0:11234`**, as requested. The local web UI is
`http://127.0.0.1:11234`; the OpenAI-compatible base URL is
`http://<MAC-TAILSCALE-IP>:11234/v1`. `macqwen status` discovers the current Tailscale
IPv4 address when the CLI is installed. Install/sign into Tailscale separately;
tailnet ACLs and the macOS firewall must permit connections from your other device.
Check `/health` and `/v1/models` from that device to verify the full network path.

**There is no API key configured. Binding `0.0.0.0` exposes the API on the LAN too,
not just Tailscale.** Do not forward this port to the public Internet. For local
use only, launch with `QWEN_HOST=127.0.0.1 macqwen start`. Tailnet traffic is protected
by Tailscale; ordinary LAN HTTP is not. Use firewall restrictions or an authenticated
proxy if you need access controls beyond your network.

The server runs in a detached process session, survives terminal closure, and
logs to `<model-dir>/.service/console.log`. No login item, launchd agent, automatic
crash restart, or reboot autostart is installed. launchd was not used because
macOS denied it access to the Documents-based log during testing. `macqwen stop`
checks process identity before sending SIGTERM and never force-kills it. `status`
returns 0 when healthy, 2 when running but not ready, and 3 when stopped. Start
waits up to 120 seconds for health and returns 2 if loading is still underway.
Do not run simultaneous start/stop commands.

Use `macqwen --help` for usage. A manual restart is
`macqwen stop && macqwen start`. The CLI reports the underlying operation's exit
code and rejects unknown commands or extra arguments without starting/stopping
anything. Renaming the CLI does not provide crash recovery or change inference.

On September 28 at 22:52 EDT, the original server (PID 73295, started 14:36)
crashed with `SIGABRT`. The macOS report identifies an invalid free in
`server.handleStreamingGeneration`, called by `server.handleChatCompletions`.
This was a runtime abort, not a stop command or reboot. The exact request-level
trigger is not established, and the underlying mlx-serve bug is not fixed by
these management scripts. Crash reports are local under
`~/Library/Logs/DiagnosticReports/mlx-serve-*.ips`; they are not included here.

## Paths and tuning

Paths contain no original-machine username. For a custom model location:

```sh
export QWEN_MODEL_DIR="/Volumes/FastSSD/Models/ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit"
./download-model.sh
./verify-model.sh
python3 install.py --model-dir "$QWEN_MODEL_DIR"
```

The installer remembers that location in the generated wrappers. Optional runtime
environment overrides are `MLX_SERVE_BIN`, `QWEN_HOST`, `QWEN_PORT` (11234),
`QWEN_CONTEXT_SIZE` (262144), `QWEN_MTP_DEPTH` (3), and `QWEN_PREFIX_CACHE_MEM`
(16GB). Keep overrides consistent for start/status/stop, for example by exporting
them in your terminal. Stop the server before changing settings. Smaller settings
are unbenchmarked here; a full prompt must leave room for output inside the native
262144-token total. Vision is intentionally disabled for these text speed tests.

## Re-run the benchmark

```sh
uv run --with tokenizers bench_server.py \
  --model-dir "$HOME/Documents/Models/ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit" \
  --model ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit \
  --depths 0,32768,260000 --max-tokens 256 --mtp on --show-output
```

Default output is prose. Use `--question` for a code task, such as
`'Write a complete Python LRU cache implementation with type hints and tests.'`.
The repeated synthetic prefix may favor prompt lookup and caching; real codebases
may perform differently. Compare actual server `prompt_tokens`, cache hits,
time-to-first-token, emitted decode rate, and output quality—not just the context
limit or a short-context headline. Restart between genuinely cold runs.

## MTPLX candidate

[MTPLX](https://github.com/youssofal/MTPLX) was reviewed, not installed or
benchmarked in this configuration. Its README reports 125.8 tok/s on an M5 Max
with an 18,539-token mostly cached prompt, versus 50.3 tok/s at 200K in another
test. These differ in hardware, model pack, and workload from our results. Its
official packs are not presented as uncensored, and compatibility with this
ARC4NUM MLX-Serve pack has not been established. The linked alternative remains
a candidate, not a validated speed upgrade.

## Local checks

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary fake model files; no GPU or model download is required.
