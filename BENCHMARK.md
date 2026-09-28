# Qwen3.8-Flash-Next local benchmark

Device: Mac Studio M3 Ultra, 80 GPU cores, 256 GiB unified memory, macOS 26.5.2.
Target: uncensored Qwen3.8-Flash-Next, native 262,144-token context, at least 80 output tokens/s in one stream.

## Models and runtimes

- OrcaRouter `Q4_K_S` GGUF, 104.08 GiB, already cached; `orcarouter-Q4_K_S` links to the existing Hugging Face snapshot.
- HauhauCS uncensored 27B `Q8_K_P` GGUF, 29.29 GiB, already cached; `hauhau-27B-Q8_K_P` links to its snapshot. This is a different, dense model, tested only as a speed alternative.
- ARC4NUM uncensored 4-bit MLX-Serve pack, 107.3 GB, downloaded in full. Its 32,000,153,976-byte n-gram sidecar matches the repository's SHA-256. `mlx-serve` 26.9.6 loads all 101 safetensors files, the native MTP head, and reports a 262,144-token model window.
- Homebrew llama.cpp 0.5.0 and mlx-serve 26.9.6.

## GGUF baseline

Command: `llama-bench -m orcarouter-Q4_K_S/Qwen3.8-Flash-Next-Uncensored-Q4_K_S-00001-of-00003.gguf -p 512 -n 128 -r 1 -ngl 99 -fa on -lm mmap --progress`

| Context depth | Prompt processing tok/s | Output tok/s |
| ---: | ---: | ---: |
| 0 | 924.57 | 42.14 |
| 32,768 | 702.38 | 30.04 |
| 131,072 | 521.23 | 17.09 |
| 260,000 | 386.68 | 10.61 |

All GGUF tests ran while the MLX pack was downloading, which can contend for SSD throughput. The 260,000-token test leaves room in the native 262,144-token window for the 512-token benchmark prompt and 128 generated tokens.

Turning off llama.cpp's lazy expert loading (`-lzm off`) did not help: 41.76 tok/s at depth 0 and 28.63 tok/s at depth 32,768, compared with 42.14 and 30.04 tok/s in the baseline.

Quantizing both K and V caches to `q8_0` (`-ctk q8_0 -ctv q8_0`) also reduced output rate: 37.86 tok/s at depth 0 and 27.84 tok/s at depth 32,768. It is a memory-saving option, not a speed win for this model on this Mac.
Using `q4_0` K/V at depth 32,768 slowed it further to 27.51 tok/s. However, at depth 260,000 it raised decode speed from 10.61 to **12.03 tok/s** (prompt processing 380.50 tok/s versus 386.68 for f16 K/V). This is a ~13% full-window decode gain, at the cost of lossy KV quantization. Use it only when prioritizing deep-context speed over exact f16-cache behavior.

Operational smoke test: `serve_gguf_full_context.sh` starts `llama-server` at the native 262,144-token setting on loopback port 11235. A real OpenAI-compatible chat request returned a coherent 54-token answer, with the server reporting 38.13 generated tok/s for its 26-token prompt. This verifies the serving command; the near-full-window figures above are from `llama-bench`, not this short API request.

Reducing CPU threads from 24 to 8 (`-t 8`) yielded 37.13 tok/s at depth 0 and 27.84 tok/s at depth 32,768, also slower than baseline.

mlx-serve's embedded `ds4` engine recognizes the OrcaRouter GGUF architecture but refuses this checkpoint because it lacks the original BF16 n-grams required by that engine. The GGUF remains usable through llama.cpp.

## Alternative model trial

The cached HauhauCS uncensored Qwen3.8-27B Q8_K_P reaches 21.68 tok/s at depth 0 and 18.35 tok/s at 32,768 (same 512-token prefill and 128-token decode test). It is slower than Flash-Next Q4_K_S at both depths, so no near-full-window run was warranted.

## MLX-Serve single-stream tests

Runtime: `mlx-serve 26.9.6`, `--ctx-size 262144 --no-vision --kv-quant 8 --kv-attn-mode fused --mtp --no-pld`; deterministic non-thinking chat, 256 output tokens, repeated synthetic archival lines for long-context tests. The `bench_server.py` client measures from first to last streamed output event, excluding prefill; timing and prompt-token counts come from real API calls. The baseline table uses the default adaptive MTP depth (up to 6), with the same prompt for serial and MTP.

| Prompt tokens | Serial output tok/s | Native MTP output tok/s | MTP time to first token |
| ---: | ---: | ---: | ---: |
| 36 | 64.60 | **87.76** | 0.84 s |
| 32,691 | 57.68 | **70.37** | 26.30 s |
| 259,932 | 53.81 | **65.13** | 206.23 s (24,576 tokens cached) |

The 259,932-token row is within the native 262,144-token window, leaving room for the 256-token output. The serial full-window comparison reused 259,901 cached prompt tokens, so its first-token delay is not comparable to the first MTP run; decode rates are comparable. The server independently reported 64.0 and 53.6 tok/s for those two full-window requests, consistent with client-streamed timing. MTP accepted 122 of 239 draft tokens in the full-window prose run (51% per-draft acceptance).

A code-generation request at 259,933 prompt tokens reached **78.66 tok/s** with default-depth MTP and 8-bit KV. At 32,691 prompt tokens, MTP with 4-bit KV reached 69.97 tok/s and unquantized KV 67.00 tok/s, compared with 70.37 tok/s for 8-bit KV. Thus 8-bit is currently the fastest tested KV mode at that depth. These are emitted-token rates, not claims about equivalent answer quality or total task time. Generic PLD was disabled, although the runtime's MTP path itself logged prompt-lookup draft engagement on the long code test; the synthetic repeated prefix may be favorable to that optimization.

### Winning full-context configuration

`./serve_mlx_best.sh` starts the same model on `0.0.0.0:11234` with **MTP depth capped at 3**, 8-bit fused KV, a 16 GB hot-prefix cache, and the native 262,144-token limit. The OpenAI-compatible base URL over this Mac's tailnet address is `http://<TAILSCALE-IP>:11234/v1` (locally, `http://127.0.0.1:11234/v1` also works); use model ID `ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit`. Binding all interfaces also exposes the server on other reachable interfaces, including the LAN. The launch script was syntax-checked; the benchmarks above used the same inference settings on loopback before this binding change.

| Prompt / output | Depth-3 MTP output tok/s | Notes |
| --- | ---: | --- |
| 259,933 prompt + 256 Python-code output | 98.04 | First run; 205.37 s to first token with 24,576 cached prompt tokens. Server reported 97.2 tok/s. |
| Same Python task, 3 warm repeats | 102.44, 102.75, 102.33 | 259,902 cached prompt tokens in each repeat. |
| Same Python task, 512 output tokens | 102.78 | Coherent LRU-cache code preview; no visible token loop. |
| 259,935 prompt + 256 Rust-code output | 101.21 | Different code task. |
| **261,424 prompt + 512 Python-code output** | **105.75** | 261,936 total tokens; **208 below** native maximum. 253,952 prompt tokens cached, 7.94 s to first token. |
| 259,932 prompt + 256 technical-prose output | 67.33 | Same depth-3 setting; below 80 for this workload. |

Depth 3 did not help at 32K (69.92 vs 70.37 tok/s with default depth), but substantially improved the full-window code trials. The code-task speed exceeds the 80 tok/s target at essentially the full native window; it is **not a guaranteed rate for arbitrary outputs**. The cold long-context prefill still took about 205 seconds in the 259,933-token test, and cached-prefix requests are much faster to first token. The model is community-labeled uncensored; refusal reduction on this specific checkpoint was not independently evaluated here.

## Apple-Silicon checkpoint search

- [Swift 1.5 Flash-Next](https://huggingface.co/ukisai/Swift-Qwen3.8-Flash-Next) is a reasoning-efficient finetune: it reports fewer *thinking tokens per answer*, not a verified 80 output tok/s at 262K. The upstream Swift checkpoint is not labeled uncensored, so it is not a direct replacement for this task.
- An [abliterated MTPLX pack](https://huggingface.co/grant-ai/Qwen3.8-Flash-Next-Abliterated-MTPLX-4bit) reports 41–44 tok/s at 26.5K and up to 67 tok/s at short context on the same M3 Ultra/256 GB hardware, but has no full-window benchmark. This makes it less promising than the requested target at 262K, and would require another 116 GB download.
- A [community oMLX benchmark](https://omlx.ai/benchmarks/performance/84jd28vl) for a different uncensored 4-bit pack on an M3 Ultra with 80 GPU cores reports 50.0 tok/s at 16K (MTP disabled); its machine has 512 GB of memory. This is context, not a measurement of the ARC4NUM pack or this Mac, and it does not establish full-window speed.
- A separate [ENGINE 8-bit checkpoint](https://huggingface.co/aniolekx/Qwen3.8-Flash-Next-E9-MLX-8bit) reports 77 tok/s near 256K on an M3 Ultra, but it is the aligned base model, tested with 512 GB RAM and a specialized runtime; it is not a directly validated uncensored configuration for this 256 GB device.
