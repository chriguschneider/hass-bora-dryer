# ADR-0002: Read the BORA through its local HTTP status pages, read-only

- **Status:** Accepted
- **Date:** 2026-10-19 (recorded retroactively; the decision dates from
  v0.1.0 and v0.2.0, 2026-05-01)

## Context

The BORA 4xx has no API. Its only network interface is a small,
unauthenticated HTTP server on the WLAN that mirrors the display: HTML
pages with the current readings, the LCD as a bitmap, and three pages that
write (clock, WLAN credentials, firmware upload). Roth-Kippe confirmed in
August 2026 that there is no control API, and a static read of firmware
V1.0.012 found no further endpoint (README, *Device control*;
`firmware/README.md`, *Writable endpoints*). The server is fragile: it is
HTTP/1.0, drops connections under fast request pacing and starves while
the dryer is drying (`tools/README.md`; comment on `PACE_SECONDS` in
`tools/probe_endpoints.py`). Facts about the pages are collected in
[`docs/upstream.md`](../upstream.md).

## Decision

- **Poll, locally, by host.** `coordinator.py` fetches `status.html` and
  `info.html` from `http://<host>/` every `SCAN_INTERVAL` (60 s) with an
  `HTTP_TIMEOUT` of 8 s (`const.py`), decodes them as UTF-8 with
  replacement, and extracts the values with the regexes `RE_*` in
  `coordinator.py`. A page without a marker yields `None` for that field,
  not an error; a connection error or HTTP error fails the update.
- **Only these requests, all `GET`:** `status.html`, `info.html`,
  `LCD.BMP?<cache-buster>` for the `Display` camera (cached
  `CAMERA_CACHE_SECONDS`, 5 s, converted to PNG in the executor), and
  `date.html?Z1=<d>&Z2=<m>&Z3=<yy>&P=0&Z4=<HH:MM:SS>&Z5=Save` only when the
  user presses *Set clock*. It is the one write the integration performs.
- **Never** request `wifi.html` (plaintext WLAN password) or
  `software.html` / `0z.bin` (firmware upload). `log-*.bin` is not used
  either: its format is unknown and a full download only works while the
  dryer is idle; using it needs an amendment here.
- **Identify the device by the 8-hex id on `info.html`** (lower-cased),
  which the config flow uses as the unique id; a body without `Bora` is
  refused as `not_a_bora`. Without a parsable id the host is used, as
  since v0.1.0.
- **Control the user can have goes through a smart plug**, never through
  the dryer: the `Power` switch and the power/energy sensors wrap entities
  the user picks in the options.

## Consequences

- A new endpoint, another write, a shorter interval or extra requests per
  poll need a new ADR (or an amendment here) first, with the evidence in
  `docs/upstream.md`.
- Firmware changes can silently break the regexes. V1.0.012 was only read
  statically; a live check after an update is a human task.
- The parser cannot be tested against real pages until captures exist:
  the page fixtures in `tests/fixtures/` are marker-only stand-ins
  (`tests/README.md`).
- `tools/` may explore further endpoints, read-only, through its
  blocklisted chokepoints (AGENTS.md, *Reverse-engineering hygiene*); a
  finding there changes the integration only through this ADR.
