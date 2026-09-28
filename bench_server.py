#!/usr/bin/env python3
"""Measure one-stream OpenAI-compatible decode speed at synthetic context depths.

Run with: uv run --with tokenizers bench_server.py --model-dir MODEL_DIR
The tokenizer is used only to size the input; the server's usage is authoritative.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from tokenizers import Tokenizer


LINE = "Record 000000: The copper lantern and quiet harbor form an archival note.\n"
QUESTION = "\nWrite a detailed, original technical essay about efficient local language-model inference. Continue for at least 400 words."


def make_prompt(tokenizer, target, question):
    if target == 0:
        return question.strip(), 0
    sample = LINE * 1000
    per_line = len(tokenizer.encode(sample, add_special_tokens=False).ids) / 1000
    count = max(1, int((target - 100) / per_line))
    content = LINE * count + question
    measured = len(tokenizer.encode(content, add_special_tokens=False).ids)
    return content, measured


def run_request(base_url, model, prompt, max_tokens, kv_quant, enable_mtp, show_output):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "enable_thinking": False,
    }
    if kv_quant is not None:
        body["kv_quant"] = kv_quant
    if enable_mtp is not None:
        body["enable_mtp"] = enable_mtp
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    first = last = None
    chunks = 0
    usage = {}
    finish = None
    output_parts = []
    try:
        with urllib.request.urlopen(request, timeout=3600) as response:
            for line in response:
                if not line.startswith(b"data: "):
                    continue
                data = line[6:].strip()
                if data == b"[DONE]":
                    break
                event = json.loads(data)
                usage = event.get("usage") or usage
                for choice in event.get("choices", []):
                    finish = choice.get("finish_reason") or finish
                    delta = choice.get("delta") or {}
                    if show_output and delta.get("content"):
                        output_parts.append(delta["content"])
                    if delta.get("content") or delta.get("reasoning_content"):
                        now = time.perf_counter()
                        first = first or now
                        last = now
                        chunks += 1
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.read().decode(errors='replace')[:1000]}") from error
    end = time.perf_counter()
    output_tokens = usage.get("completion_tokens")
    decode_seconds = None if first is None or last <= first else last - first
    result = {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": output_tokens,
        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "time_to_first_token_s": None if first is None else round(first - start, 3),
        "decode_seconds": None if decode_seconds is None else round(decode_seconds, 3),
        "output_tokens_per_second": None if not decode_seconds or not output_tokens else round((output_tokens - 1) / decode_seconds, 2),
        "wall_seconds": round(end - start, 3),
        "stream_chunks": chunks,
        "finish_reason": finish,
    }
    if show_output:
        result["output_preview"] = "".join(output_parts)[:1200]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:11234")
    parser.add_argument("--model", default="mlx-serve")
    parser.add_argument("--depths", default="0,32768,131072,260000")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--show-output", action="store_true")
    parser.add_argument("--kv-quant", choices=["off", "4", "8"])
    parser.add_argument("--mtp", choices=["on", "off"])
    args = parser.parse_args()
    tokenizer = Tokenizer.from_file(str(args.model_dir / "tokenizer.json"))
    for depth in (int(item) for item in args.depths.split(",")):
        prompt, text_tokens = make_prompt(tokenizer, depth, args.question)
        result = run_request(args.url, args.model, prompt, args.max_tokens, args.kv_quant, None if args.mtp is None else args.mtp == "on", args.show_output)
        print(json.dumps({"target_depth": depth, "raw_text_tokens": text_tokens, "kv_quant": args.kv_quant, "mtp": args.mtp, **result}), flush=True)


if __name__ == "__main__":
    main()
