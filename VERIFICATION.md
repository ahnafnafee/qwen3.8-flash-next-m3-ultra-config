# Verification record

Executed September 28, 2026 on the M3 Ultra / 256 GiB Mac described in
[BENCHMARK.md](BENCHMARK.md).

- Six offline unit tests passed: shell/Python syntax, installed launch arguments,
  spaces/apostrophes in paths, repeat installation, conflict refusal and backup,
  unchanged weight fixtures, symlink refusal, unrelated-PID rejection, and pinned
  Hugging Face CLI arguments. Some tests cover several of these checks.
- A separate read-only verifier found no publishing blockers in the scripts,
  installer, documentation, portability, and sensitive-file exclusions.
- `hf cache verify` completed successfully against the pinned model revision:
  **113 upstream files checked**, with no missing-file or checksum failure.
  It warned about extra local cache/management files, which are allowed; the
  verification command intentionally does not reject extras.
- Real server lifecycle passed: start, idempotent start, stop, stopped status,
  repeated stop, restart, and persistence after the starting command exited.
- The portable installer was applied to the actual model directory. Earlier
  management scripts were backed up; model weights were not modified.
- The restarted server listened on IPv4 `*:11234`. `/health` succeeded through
  this Mac's Tailscale IPv4 address, and `/v1/models` advertised 262144 tokens,
  MTP loaded, and 8-bit KV. Connectivity from a separate tailnet peer was **not**
  tested, so remote firewall/ACL reachability is not certified here.
- A real non-thinking chat smoke test returned a correct Python square function
  (29 prompt tokens, 20 output tokens). This short check verifies operation; it
  is not a substitute for the near-full-context benchmarks.
- No model weights, runtime logs, caches, access tokens, or original-machine
  usernames/tailnet addresses are included in this configuration repo.

Fresh download of the 107 GB pack on a second Mac, lower-memory behavior, and
MTPLX compatibility/performance have not been tested. The download dry run,
installed-model checksum verification, and portable installer tests provide
replication checks without duplicating the large model locally.

## macqwen CLI update (September 28, 2026, evening)

- Added and installed `macqwen start`, `macqwen stop`, and `macqwen status`,
  preserving the old `qwen-*` aliases and model-directory scripts.
- All **8** offline tests passed, including command dispatch, exit-code
  propagation, help/invalid-argument handling, installed wrapper paths with
  spaces/apostrophes, and compatibility aliases. Shell syntax, Python parsing,
  and whitespace checks passed; independent read-only review found no blockers.
- Verified real start, repeated start, stop, stopped status (exit 3), repeated
  stop, restart, detached persistence, and health through the Mac's own
  Tailscale address. Left the server running on `0.0.0.0:11234`.
- The earlier process's local crash report confirms a self-abort (`SIGABRT`)
  at 22:52 EDT from an invalid free in the runtime's streaming handler. No
  inference settings were changed, and this update does **not** claim to fix
  the underlying mlx-serve memory bug or add automatic crash recovery.
