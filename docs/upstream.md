# Upstream facts

Measured facts about every external system this repo talks to: endpoints,
file formats, units, update cadence, limits, quirks. Agents read this file
before they touch anything that depends on an upstream, and every lookup
table or constant in the code cites a line here, a URL or a fixture.

Write what you **measured**, with the date and how (command, file), not what
a documentation page promises. When the upstream changes, add a dated entry
instead of rewriting history.

This repo has one upstream: the BORA's embedded web server. Everything
below is collected from files already in the repo (cited per line); it was
not re-measured when this file was written (2026-10-19). Decision on how
it is used: [ADR-0002](adr/0002-local-http-status-pages.md).

## BORA 4xx embedded web server

- **Measured:**
  - Live on a **BORA 410, firmware V1.0.006** (README, *Supported models*;
    the parser in `custom_components/bora_dryer/coordinator.py` was written
    against it). No date recorded in the repo.
  - Statically, from the image **`WT05-V1.0.012.bin`**, 2026-09-30, with
    `strings`, `file` and an entropy script (`firmware/README.md`,
    *Static analysis*). Not run on a device.
  - Endpoint recon with `tools/probe_endpoints.py` and the log campaign with
    `tools/log_capture.py` (`tools/README.md`); their results are
    gitignored and not in the repo.
- **Transport:** plain HTTP on port 80 of the device's WLAN address, **no
  authentication** (README, *Security note*). The server speaks HTTP/1.0
  (`tools/README.md`; `tools/probe_endpoints.py`, comment on
  `PACE_SECONDS`). The dryer can also open its own access point at
  `192.168.4.1` (README, *Firmware updates*).

### Pages and what is read from them

| Path | Used by | What is read | Source |
|---|---|---|---|
| `status.html` | coordinator | `Present Temperature: <x> °C`, `Present RH: <n> %`, `Present Operation: <text><` | `coordinator.py` `RE_TEMPERATURE`, `RE_HUMIDITY`, `RE_OPERATION`; `firmware/README.md` (template variables `$vp0`, `$vp1`, `$vp5`; markers unchanged in V1.0.012) |
| `info.html` | coordinator, config flow | `V<x.y.z><br>` followed by the 8-hex device id and `<br>`; `Bora <model>`; `Filter <h>:<m>` | `coordinator.py` `RE_FIRMWARE`, `RE_DEVICE_ID`, `RE_MODEL`, `RE_FILTER`; `config_flow.py` `_probe`; `firmware/README.md` (`$vT0`, `$vV0`, `$vV1`, `$vV3`) |
| `LCD.BMP?<cache-buster>` | camera | the current LCD screen as a BMP | `camera.py`; `firmware/README.md` (`$vV2`) |
| `date.html?Z1=<d>&Z2=<m>&Z3=<yy>&P=0&Z4=<HH:MM:SS>&Z5=Save` | button | **write**: sets the clock; the same parameters the device's own page sends | `button.py`; `firmware/README.md`, *Writable endpoints* |

- **Operation texts** seen: `Standby`, `Drying` (README, *Entities*). The
  `Drying` binary sensor is on when the text contains `Drying`
  (`binary_sensor.py`). The full set of texts is not documented.
- **Device id:** 8 hex digits, also part of the access-point SSID
  `Bora 4xx-<id>` (`firmware/README.md`, `$vV1`). The integration lower-cases
  it (`coordinator.py`, `config_flow.py`).
- **Model:** the page title is e.g. `Bora 410` (`firmware/README.md`,
  `$vT0`); the 4xx series is 408 / 410 / 415 / 420 (README, *Supported
  models*). The `H` suffix (e.g. `Bora 420 H`) is the heater variant
  (`firmware/README.md`, *Provenance*); whether `RE_MODEL` sees it is
  unverified.
- **Firmware string:** `V1.0.006`, `V1.0.012`; the parser stores it without
  the leading `V` (`RE_FIRMWARE` captures the digits only).
- **Filter counter:** `Filter hh:mm`, operating hours and minutes since the
  last reset on the device (`firmware/README.md`, `$vV3`). The device warns
  at 300 h (`const.py`, `FILTER_LIFETIME_HOURS`); the reset is only possible
  on the display (*Filter gereinigt*, `firmware/README.md`).

### Pages the integration does not use

| Path | Why | Source |
|---|---|---|
| `wifi.html` (`?S0=<ssid>&S1=<password>&es=Save`) | **never**: shows the WLAN password in plaintext; the query writes credentials | README, *Security note*; `firmware/README.md` |
| `software.html`, `0z.bin` (`POST multipart/form-data`) | **never**: firmware upload, unauthenticated, no signature check | README, *Firmware updates*; `firmware/README.md` |
| `log-<title>-<device-id>-<version>.bin` | not used yet: packed binary, format unknown, only transfers fully while idle (ADR-0002) | `tools/README.md`; `tools/log_capture.py` |

Every file the server can serve (from the V1.0.012 resource table):
`index*.html`, `status*.html`, `date*.html`, `software*.html`,
`wifi*.html` (each also with `_g`, `_f`, `_i` language variants),
`lcd.html`, `info.html`, `menu.png`, `refresh.png`, `favicon.ico`,
`language.bin` (`firmware/README.md`). There is **no** start, stop,
program or filter-reset endpoint.

### Cadence and limits

- The integration polls every 60 s, timeout 8 s, both pages concurrently
  (`const.py` `SCAN_INTERVAL`, `HTTP_TIMEOUT`; `coordinator.py`). The camera
  fetches the bitmap at most every 5 s (`CAMERA_CACHE_SECONDS`).
- **Fragile under load:** pacing of 0.15 s with a 5 s read timeout gave
  about 20 % timeouts on a healthy device; the probe tool defaults to 0.5 s
  and 8 s (`tools/probe_endpoints.py`).
- **Starves while drying:** under an active cycle `status.html` goes flaky
  and large downloads truncate (`tools/README.md`).
- **Offline is normal:** the dryer is often switched off at the plug; the
  integration treats an unreachable host as a failed poll, not an error
  (CHANGELOG v0.3.2, v0.5.1, v0.8.0).

### Unknown (capture before relying on it)

- The full HTML of `status.html` and `info.html` around the markers, the
  `Content-Type` and the character encoding the device sends (the parser
  decodes UTF-8 with replacement and expects a literal `°C`).
- The behaviour of other models and of V1.0.012 on a live device.
