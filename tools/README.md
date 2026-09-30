# tools/ — developer scripts

This folder is for **developer / reverse-engineering tooling**, not for end users
of the integration. HACS users do not need to run anything here.

## probe_endpoints.py

Recon script that probes the BORA dryer's HTTP interface for undocumented
endpoints. Read-only by design: a hard-coded blocklist (`Z5=Save`, `0z.bin`)
and a method whitelist guard the single `safe_request()` chokepoint.

### Run

```powershell
# Self-test: verifies safety assertions (no network I/O)
python tools/probe_endpoints.py --self-test

# Dry-run against an unreachable target (sanity-check error handling)
python tools/probe_endpoints.py --host 127.0.0.1 --port 1

# Live run against the device
python tools/probe_endpoints.py --host 192.168.23.169

# Slower pacing if the device times out a lot (defaults: pace=0.5s, timeout=8s)
python tools/probe_endpoints.py --host 192.168.23.169 --pace 1.0 --timeout 15
```

### Behavior on failure

If all three baseline probes (`/index.html`, `/`, and a deliberately-bogus
path) error out, the script aborts with exit code 2 instead of running the
full sweep — without a baseline, every fallback response would be
misclassified as a FIND. Re-run with a higher `--timeout` or `--pace`.

### Output

- Stdout: live `[!] FIND` lines while probing, then a sorted summary table.
- File: `tools/probe_results/probe_<UTC-timestamp>.json` with the full report
  (every request: status, length, headers, body hash, snippet).

`tools/probe_results/` is `.gitignore`d — results may include device fingerprint
data (and `/wifi.html` exposes the WLAN password in plaintext, so do not paste
raw output anywhere).

### Wordlist

`wordlists/paths.txt` — one base name per line. Bare words are expanded with
common suffixes (`.html`, `.htm`, `.cgi`, `.txt`, `.xml`, `.json`); entries
containing `.` or `/` are used literally.

## log_capture.py / log_decode.py — the `log-*.bin` decode campaign

`status.html` links a **Download Log** file (`GET /log-<model>-<id>-<version>.bin`):
a persistent (flash-backed, append-only) recording the device keeps. It is a
*packed* binary stream — a 2-byte token structure, ~5.2 bits/byte entropy, not
plain temperature/RH samples — so it can't be read directly. These two scripts
collect the ground truth needed to reverse it.

`log_capture.py` is read-only (GET on `status.html`, `info.html` and the
`log-*.bin` path only). It samples the live readings on `--interval` and grabs
full log snapshots, writing `samples.csv`, `logs.csv` and `logs/log_<epoch>.bin`
under `tools/log_capture_results/` (git-ignored).

```
python tools/log_capture.py --host 192.168.23.169 --interval 30
python tools/log_decode.py tools/log_capture_results/run_<ts>
```

`log_decode.py` pairs each *complete* snapshot with the status rows in its
window and dumps the appended tail bytes, i.e. "known reading ↔ new bytes".

### The device constraint that shapes the campaign

The full log transfers **only while the device is idle**. Under an active
drying cycle the BORA's HTTP/1.0 server starves: `status.html` goes flaky and
the log truncates at the same early offset every time (~4 KB of the *old* head,
never the new tail). So partial downloads during drying are useless — the new
data is reachable only in a complete, idle download.

Because the log is persistent across power cycles, the workable protocol is
**opportunistic full captures at idle**: grab a complete log in the responsive
window right after power-on (before drying loads the CPU), keep status sampling
running, and let successive complete snapshots — which grow as history is
appended — supply the windows `log_decode.py` lines up against the readings.
Use a longer `--log-timeout` (60–90 s) when you expect a full idle download.
