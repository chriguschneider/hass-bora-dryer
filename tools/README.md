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
