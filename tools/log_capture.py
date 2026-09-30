#!/usr/bin/env python3
"""Ground-truth capture campaign for the BORA `log-*.bin` endpoint.

The device exposes an internal recording at

    GET /log-<model>-<id>-<version>.bin   (linked as "Download Log" on status.html)

It is a persistent (flash-backed), append-only, *packed* binary stream — not
plain telemetry. To reverse the packing we need ground truth: the live
temperature / RH / operation read from `status.html` at known wall-clock times,
paired with full log snapshots, so that "known reading over this window" can be
matched to "bytes appended to the log over this window".

This script collects exactly that, read-only:

  * every --interval seconds: GET status.html + info.html, append one row to
    samples.csv (epoch, iso, temp, rh, operation, filter);
  * every --log-every samples, and whenever `operation` changes: download the
    full log to logs/log_<epoch>.bin and record its size + sha256 in logs.csv.

The full log only transfers completely while the device is idle — under an
active drying cycle its HTTP/1.0 server starves and truncates. The script
records the byte count it actually received so truncated snapshots are visible
(and skipped) during analysis; see log_decode.py.

SAFETY: read-only. The single chokepoint `get()` allows GET only, and only for
status.html, info.html and a path that must match the log-*.bin pattern. It
never writes, so it can never set the clock, change WiFi or upload firmware.

Run:  python tools/log_capture.py --host 192.168.23.169 --interval 30
Stop: Ctrl-C (writes a final log snapshot on the way out).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "tools" / "log_capture_results"

LOG_PATH_RE = re.compile(r"^/log-.+\.bin$")
HREF_LOG_RE = re.compile(r'href="(log-[^"]+\.bin)"')
RE_TEMPERATURE = re.compile(r"Present Temperature:\s*(-?\d+(?:\.\d+)?)\s*°C")
RE_HUMIDITY = re.compile(r"Present RH:\s*(\d+)\s*%")
RE_OPERATION = re.compile(r"Present Operation:\s*([^<\n]+?)\s*<")
RE_FILTER = re.compile(r"Filter\s*(\d+):(\d+)")

HTTP_TIMEOUT = 8
# The log transfers fully only while the device is idle; under an active drying
# cycle its server dribbles bytes and then truncates. Cap the wait so a stalled
# download can't starve status sampling — truncated snapshots are detected and
# skipped in log_decode.py anyway. Override with --log-timeout.
LOG_TIMEOUT = 30


def get(host: str, port: int, path: str, timeout: int) -> tuple[int, bytes]:
    """Single read-only chokepoint. GET only; path must be a known-safe page
    or match the log-*.bin pattern. Raises before any I/O otherwise."""
    assert path.startswith("/"), f"path must start with '/': {path!r}"
    bare = path.split("?", 1)[0]
    assert bare in ("/status.html", "/info.html") or LOG_PATH_RE.match(bare), (
        f"path not allowed for capture: {path!r}"
    )
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).astimezone().isoformat(timespec="seconds")


def read_status(host: str, port: int) -> dict:
    """Return parsed status+info, or {} on any failure (never raises)."""
    out: dict = {}
    try:
        _, body = get(host, port, "/status.html", HTTP_TIMEOUT)
        text = body.decode("utf-8", "replace")
        if m := RE_TEMPERATURE.search(text):
            out["temp"] = m.group(1)
        if m := RE_HUMIDITY.search(text):
            out["rh"] = m.group(1)
        if m := RE_OPERATION.search(text):
            out["operation"] = m.group(1).strip()
        if m := HREF_LOG_RE.search(text):
            out["log_href"] = m.group(1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out["status_error"] = repr(exc)
    try:
        _, body = get(host, port, "/info.html", HTTP_TIMEOUT)
        text = body.decode("utf-8", "replace")
        if m := RE_FILTER.search(text):
            out["filter"] = f"{m.group(1)}:{m.group(2)}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out.setdefault("status_error", repr(exc))
    return out


def download_log(host: str, port: int, log_href: str, logs_dir: Path, epoch: float,
                 timeout: int = LOG_TIMEOUT) -> dict:
    """Fetch the full log, save it, return a manifest row. Never raises."""
    from urllib.parse import quote

    path = "/" + quote(log_href)  # the href contains a space (model name)
    row = {"epoch": f"{epoch:.0f}", "iso": iso(epoch), "href": log_href}
    try:
        status, data = get(host, port, path, timeout)
        fn = logs_dir / f"log_{epoch:.0f}.bin"
        fn.write_bytes(data)
        row.update(
            http=status,
            bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            file=fn.name,
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        row.update(http="", bytes="", sha256="", file="", error=repr(exc))
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--host", required=True, help="BORA IP, e.g. 192.168.23.169")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--interval", type=float, default=30.0, help="status sample seconds")
    ap.add_argument("--log-every", type=int, default=20, help="download log every N samples")
    ap.add_argument("--log-timeout", type=int, default=LOG_TIMEOUT,
                    help=f"seconds to wait for a log download (default {LOG_TIMEOUT}); "
                         "raise it for full idle captures, keep low during drying")
    ap.add_argument("--duration", type=float, default=0, help="stop after N seconds (0 = until Ctrl-C)")
    ap.add_argument("--outdir", default=None, help="override results dir")
    args = ap.parse_args(argv)

    run_dir = Path(args.outdir) if args.outdir else RESULTS_DIR / f"run_{int(time.time())}"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    samples_csv = run_dir / "samples.csv"
    logs_csv = run_dir / "logs.csv"
    print(f"[capture] writing to {run_dir}")

    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))

    s_fields = ["epoch", "iso", "temp", "rh", "operation", "filter", "status_error"]
    l_fields = ["epoch", "iso", "href", "http", "bytes", "sha256", "file", "error"]
    sf = samples_csv.open("w", newline="")
    lf = logs_csv.open("w", newline="")
    sw = csv.DictWriter(sf, fieldnames=s_fields, extrasaction="ignore")
    lw = csv.DictWriter(lf, fieldnames=l_fields, extrasaction="ignore")
    sw.writeheader()
    lw.writeheader()

    start = time.time()
    last_op = None
    log_href = None
    n = 0
    try:
        while not stop["flag"]:
            t = time.time()
            st = read_status(args.host, args.port)
            st["epoch"] = f"{t:.0f}"
            st["iso"] = iso(t)
            sw.writerow(st)
            sf.flush()
            log_href = st.get("log_href", log_href)
            op = st.get("operation")
            print(f"[{iso(t)}] temp={st.get('temp','?')} rh={st.get('rh','?')} "
                  f"op={op or st.get('status_error','?')} filter={st.get('filter','?')}")

            op_changed = op is not None and op != last_op
            if log_href and (n % args.log_every == 0 or op_changed):
                row = download_log(args.host, args.port, log_href, logs_dir, t, args.log_timeout)
                lw.writerow(row)
                lf.flush()
                note = row.get("error") or f"{row['bytes']} bytes"
                print(f"    -> log snapshot: {note}")
            last_op = op if op is not None else last_op
            n += 1

            if args.duration and (time.time() - start) >= args.duration:
                break
            # responsive sleep so Ctrl-C is quick
            slept = 0.0
            while slept < args.interval and not stop["flag"]:
                time.sleep(min(0.5, args.interval - slept))
                slept += 0.5

        # final full snapshot on exit
        if log_href:
            row = download_log(args.host, args.port, log_href, logs_dir, time.time(), args.log_timeout)
            lw.writerow(row)
            print(f"[capture] final log snapshot: {row.get('error') or str(row['bytes']) + ' bytes'}")
    finally:
        sf.close()
        lf.close()
    print(f"[capture] done. {n} samples in {samples_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
