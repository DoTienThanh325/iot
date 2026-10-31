"""Benchmark a running API with fresh independent sessions (never cached replays)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
import uuid

import httpx
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001/api/v2/analyze")
    parser.add_argument("--input", default="examples/analyze_v2.json")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 32:
        parser.error("requests must be 1..10000 and concurrency 1..32")
    template = json.loads(Path(args.input).read_text())
    run = uuid.uuid4().hex[:12]

    with httpx.Client(timeout=30) as client:
        def send(index):
            body = deepcopy(template)
            body["session_id"] = f"benchmark-{run}-{index}"
            body["window_id"] = "window-1"
            start = perf_counter()
            try:
                response = client.post(args.url, json=body)
                return response.status_code, perf_counter() - start
            except httpx.HTTPError:
                return "transport_error", perf_counter() - start
        start = perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(send, range(args.requests)))
        elapsed = perf_counter() - start
    successes = [duration for status, duration in results if status == 200]
    report = {
        "scope": "independent sessions; includes HTTP, analysis and persistence; not cached replays",
        "requests": args.requests, "concurrency": args.concurrency,
        "status_counts": {str(status): sum(s == status for s, _ in results) for status, _ in results},
        "elapsed_seconds": elapsed, "successful_requests_per_second": len(successes) / elapsed,
        "success_latency_ms": None if not successes else {
            "mean": mean(successes) * 1000,
            "p50": float(np.quantile(successes, .5) * 1000),
            "p95": float(np.quantile(successes, .95) * 1000),
            "p99": float(np.quantile(successes, .99) * 1000),
        },
    }
    text = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
