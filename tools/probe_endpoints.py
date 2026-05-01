#!/usr/bin/env python3
"""HTTP-Endpoint recon for the BORA 410 dryer web interface.

Reads tools/wordlists/paths.txt, probes each path against the device, and
classifies responses against the known index-fallback baseline.

SAFETY: this script never issues writes. A hard-coded blocklist
(`Z5=Save`, `0z.bin`) and a method whitelist are enforced at the
single chokepoint `safe_request()`. Bypassing them raises before any
socket I/O.

Run:  python tools/probe_endpoints.py --host 192.168.23.169
Dry:  python tools/probe_endpoints.py --host 127.0.0.1 --port 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import string
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDLIST = REPO_ROOT / "tools" / "wordlists" / "paths.txt"
RESULTS_DIR = REPO_ROOT / "tools" / "probe_results"

FORBIDDEN_SUBSTRINGS = ("Z5=Save", "0z.bin")
ALLOWED_METHODS_UNKNOWN_PATHS = {"GET", "HEAD"}
ALLOWED_METHODS_KNOWN_SAFE_PATHS = {"GET", "HEAD", "OPTIONS"}
KNOWN_SAFE_PATHS = {
    "/index.html",
    "/status.html",
    "/info.html",
    "/lcd.html",
    "/wifi.html",
    "/software.html",
}

EXPANSION_SUFFIXES = ("", ".html", ".htm", ".cgi", ".txt", ".xml", ".json")
PRINTABLE = set(string.printable) - {"\x0b", "\x0c"}
SNIPPET_LEN = 200

# Defaults, overridable via CLI. Slow defaults: the BORA's HTTP/1.0 server
# starts dropping connections under aggressive pacing — empirically 0.15s with
# a 5s read timeout produced ~20% timeout rate on a healthy device.
PACE_SECONDS = 0.5
HTTP_TIMEOUT = 8


def safe_request(host: str, port: int, method: str, path: str) -> dict:
    """Single chokepoint for HTTP. Enforces safety rules, then performs the call."""
    assert path.startswith("/"), f"path must start with '/': {path!r}"
    for needle in FORBIDDEN_SUBSTRINGS:
        assert needle not in path, f"forbidden substring {needle!r} in path {path!r}"

    bare = path.split("?", 1)[0]
    if bare in KNOWN_SAFE_PATHS:
        allowed = ALLOWED_METHODS_KNOWN_SAFE_PATHS
    else:
        allowed = ALLOWED_METHODS_UNKNOWN_PATHS
    assert method in allowed, f"method {method} not allowed for path {path!r}"

    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url, method=method)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            body = resp.read()
            status = resp.status
            headers = dict(resp.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        status = exc.code
        headers = dict(exc.headers.items()) if exc.headers else {}
    except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
        return {
            "url": url,
            "method": method,
            "path": path,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }

    snippet = "".join(
        c if c in PRINTABLE else "."
        for c in body[: SNIPPET_LEN * 2].decode("utf-8", errors="replace")
    )[:SNIPPET_LEN]

    return {
        "url": url,
        "method": method,
        "path": path,
        "status": status,
        "content_length": len(body),
        "content_type": headers.get("Content-Type", ""),
        "headers": headers,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_snippet": snippet,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


def load_wordlist(path: Path) -> list[str]:
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def expand_paths(words: list[str]) -> list[str]:
    """Return absolute paths to probe. Words containing '.', '/', or trailing '/' are used literally."""
    out: list[str] = []
    seen: set[str] = set()
    for w in words:
        if "." in w or "/" in w:
            candidates = [w]
        else:
            candidates = [f"{w}{suf}" for suf in EXPANSION_SUFFIXES]
        for c in candidates:
            p = "/" + c.lstrip("/")
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


def classify(result: dict, fallback_hashes: set[str]) -> str:
    if "error" in result:
        return "ERROR"
    status = result.get("status", 0)
    if status == 200:
        if result.get("body_sha256") in fallback_hashes:
            return "FALLBACK"
        return "FIND"
    if status in (301, 302, 303, 307, 308):
        return "REDIRECT"
    if status == 404:
        return "404"
    return f"HTTP_{status}"


def run(host: str, port: int) -> dict | None:
    print(f"[+] target = http://{host}:{port}  (pace={PACE_SECONDS}s, timeout={HTTP_TIMEOUT}s)")
    print("[+] baseline ...")
    baseline_index = safe_request(host, port, "GET", "/index.html")
    baseline_root = safe_request(host, port, "GET", "/")
    bogus = safe_request(host, port, "GET", "/__claude_probe_404__")

    fallback_hashes: set[str] = set()
    for r in (baseline_index, baseline_root, bogus):
        if "body_sha256" in r:
            fallback_hashes.add(r["body_sha256"])
    print(f"[+] fallback hashes collected: {len(fallback_hashes)}")
    if not fallback_hashes:
        print("[!] BASELINE FAILED — all three baseline probes errored.")
        for r in (baseline_index, baseline_root, bogus):
            print(f"    {r.get('path'):25} -> {r.get('error', '?')}")
        print(f"    Without a baseline every fallback response would be misclassified")
        print(f"    as FIND. Aborting. Try --timeout {HTTP_TIMEOUT * 2} or --pace {PACE_SECONDS * 2}.")
        return None

    words = load_wordlist(WORDLIST)
    paths = expand_paths(words)
    print(f"[+] probing {len(paths)} paths (GET) ...")

    results: list[dict] = []
    for i, p in enumerate(paths, 1):
        r = safe_request(host, port, "GET", p)
        r["kind"] = classify(r, fallback_hashes)
        results.append(r)
        if r["kind"] == "FIND":
            print(f"  [!] FIND  {p}  status={r.get('status')} len={r.get('content_length')}")
        time.sleep(PACE_SECONDS)
        if i % 25 == 0:
            print(f"  ... {i}/{len(paths)}")

    print("[+] verb probe on known-safe paths ...")
    verb_results: list[dict] = []
    for path in sorted(KNOWN_SAFE_PATHS):
        for method in ("HEAD", "OPTIONS"):
            r = safe_request(host, port, method, path)
            r["kind"] = "VERB"
            verb_results.append(r)
            if "headers" in r:
                allow = r["headers"].get("Allow") or r["headers"].get("allow")
                if allow:
                    print(f"  [!] {method} {path}  Allow: {allow}")
            time.sleep(PACE_SECONDS)

    print("[+] /date.html parameter sniff (read-only) ...")
    date_results = [
        safe_request(host, port, "GET", "/date.html"),
        safe_request(host, port, "GET", "/date.html?"),
        safe_request(host, port, "GET", "/date.html?P=0"),
    ]
    for r in date_results:
        r["kind"] = "DATE_SNIFF"
    time.sleep(PACE_SECONDS)

    return {
        "host": host,
        "port": port,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": [baseline_index, baseline_root, bogus],
        "path_probe": results,
        "verb_probe": verb_results,
        "date_sniff": date_results,
    }


def print_summary(report: dict) -> None:
    rows = [r for r in report["path_probe"]]
    rows.sort(key=lambda r: (r.get("kind") != "FIND", r.get("kind", ""), r.get("path", "")))
    print()
    print(f"{'KIND':<10} {'STATUS':<7} {'LEN':<8} PATH")
    print("-" * 70)
    for r in rows:
        print(
            f"{r.get('kind','?'):<10} "
            f"{str(r.get('status','-')):<7} "
            f"{str(r.get('content_length','-')):<8} "
            f"{r.get('path','')}"
        )
    finds = [r for r in rows if r.get("kind") == "FIND"]
    print()
    print(f"[=] total probed: {len(rows)}, FINDs: {len(finds)}")


def main(argv: list[str]) -> int:
    global PACE_SECONDS, HTTP_TIMEOUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", help="Device host/IP, e.g. 192.168.23.169")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--pace", type=float, default=PACE_SECONDS,
                    help=f"Seconds between requests (default {PACE_SECONDS})")
    ap.add_argument("--timeout", type=float, default=HTTP_TIMEOUT,
                    help=f"Per-request HTTP timeout in seconds (default {HTTP_TIMEOUT})")
    ap.add_argument("--out", type=Path, default=None, help="Optional explicit output JSON path")
    ap.add_argument("--self-test", action="store_true", help="Run safety assertions and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.host:
        ap.error("--host is required (unless --self-test)")

    PACE_SECONDS = args.pace
    HTTP_TIMEOUT = args.timeout

    report = run(args.host, args.port)
    if report is None:
        return 2
    print_summary(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = args.out or RESULTS_DIR / f"probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[+] full report: {out}")
    return 0


def _self_test() -> int:
    print("[self-test] forbidden substrings should raise")
    for bad in ("/date.html?Z5=Save", "/0z.bin", "/foo?x=Z5=Save"):
        try:
            safe_request("127.0.0.1", 1, "GET", bad)
        except AssertionError as exc:
            print(f"  ok  {bad!r:40} -> {exc}")
        else:
            print(f"  FAIL  {bad!r} did not raise")
            return 1

    print("[self-test] write methods on unknown paths should raise")
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        try:
            safe_request("127.0.0.1", 1, method, "/anything")
        except AssertionError as exc:
            print(f"  ok  {method:8} -> {exc}")
        else:
            print(f"  FAIL  {method} on unknown path did not raise")
            return 1

    print("[self-test] write methods on known-safe paths should also raise")
    for method in ("POST", "PUT", "DELETE"):
        try:
            safe_request("127.0.0.1", 1, method, "/status.html")
        except AssertionError as exc:
            print(f"  ok  {method:8} on /status.html -> {exc}")
        else:
            print(f"  FAIL  {method} /status.html did not raise")
            return 1

    print("[self-test] OPTIONS on unknown path should raise (only GET/HEAD allowed)")
    try:
        safe_request("127.0.0.1", 1, "OPTIONS", "/whatever")
    except AssertionError as exc:
        print(f"  ok  -> {exc}")
    else:
        print("  FAIL  OPTIONS on unknown path did not raise")
        return 1

    print("[self-test] all assertions hold")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
