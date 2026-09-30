#!/usr/bin/env python3
"""Analysis scaffold for a log_capture.py run.

Given a capture run directory, this pairs the ground-truth status samples with
the full log snapshots so the packed `log-*.bin` stream can be reversed:

  * lists log snapshots by time, flags truncated ones (a snapshot is usable
    only if it is a byte-exact prefix extension of the previous one — the log
    is append-only, so a good capture never shrinks or diverges);
  * for each consecutive pair of *complete* snapshots, prints how many bytes
    were appended and the status rows that fall in that window — i.e. the
    known (temp, rh, operation) series that those new bytes must encode;
  * dumps the appended tail bytes as hex so the packing can be inspected
    against the known readings.

This does not itself decode the format — it turns the raw capture into the
"known reading <-> new bytes" pairs needed to work it out. Run it after a
capture that spans at least one full drying cycle plus idle time on both ends
(idle is when the full log actually transfers).

Run:  python tools/log_decode.py tools/log_capture_results/run_<ts>
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("run_dir", help="a log_capture_results/run_* directory")
    ap.add_argument("--hex", type=int, default=64, help="tail hex bytes to dump per window")
    args = ap.parse_args(argv)

    run = Path(args.run_dir)
    samples = load_rows(run / "samples.csv")
    logs = load_rows(run / "logs.csv")
    if not logs:
        print("no logs.csv rows — run log_capture.py first", file=sys.stderr)
        return 2

    # Load snapshot bytes, ordered by epoch.
    snaps = []
    for row in sorted(logs, key=lambda r: int(r["epoch"] or 0)):
        if not row.get("file"):
            continue
        data = (run / "logs" / row["file"]).read_bytes()
        snaps.append((int(row["epoch"]), data, row))

    print(f"{len(snaps)} log snapshots, {len(samples)} status samples\n")
    print(f"{'epoch':>10} {'bytes':>8}  prefix-of-next?  note")
    complete = []
    for i, (ep, data, row) in enumerate(snaps):
        note = ""
        if i + 1 < len(snaps):
            nxt = snaps[i + 1][1]
            if len(nxt) >= len(data) and nxt[: len(data)] == data:
                note = "append-only OK"
                complete.append((ep, data, row))
            elif len(data) >= len(snaps[i + 1][1]) and data[: len(nxt)] == nxt:
                note = "next is TRUNCATED (skip next)"
                complete.append((ep, data, row))
            else:
                note = "DIVERGES — one side truncated"
        print(f"{ep:>10} {len(data):>8}  {'':>15}  {note}")

    # Windows between consecutive complete snapshots.
    print("\n=== append windows (known readings <-> new bytes) ===")
    for (ep0, d0, _), (ep1, d1, _) in zip(complete, complete[1:]):
        if len(d1) <= len(d0) or d1[: len(d0)] != d0:
            continue
        appended = d1[len(d0):]
        rows = [s for s in samples if ep0 <= int(s["epoch"] or 0) <= ep1]
        print(f"\n[{ep0} -> {ep1}]  +{len(appended)} bytes over {ep1 - ep0}s, "
              f"{len(rows)} status samples")
        for s in rows:
            print(f"    {s['iso']}  temp={s.get('temp','?')} rh={s.get('rh','?')} "
                  f"op={s.get('operation','?')}")
        tail = appended[: args.hex]
        print("    new bytes:", tail.hex())
    return 0


if __name__ == "__main__":
    sys.exit(main())
