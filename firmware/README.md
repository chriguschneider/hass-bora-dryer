# firmware/ — vendor firmware archive

Roth-Kippe sends the current BORA firmware to owners on request (see
[issue #3](https://github.com/chriguschneider/hass-bora-dryer/issues/3)).
This folder keeps a local copy plus the vendor's update instructions.

**The binaries are not in git** (`firmware/*.bin`, `firmware/*.pdf` are
ignored). They are Roth-Kippe's software; we have no permission to
redistribute them. Owners who want the file should ask Roth-Kippe directly —
they answered within the day.

## Provenance

| File | Source | SHA-256 |
|---|---|---|
| `WT05-V1.0.012.bin` (781 208 bytes) | E-mail from Roth-Kippe (Teamleiterin Raumluft-Wäschetrockner), 2026-09-17, reply to our firmware request of 2026-08-23 | `bfb6f3efa0879c71c1af9bda4cd051c32e46df620bd2babe9d64f604cd876d3b` |
| `Bedienungsanleitung-Software-Update-BORA.pdf` (324 365 bytes) | same e-mail | `6d52a59687e1593152fb3b25550e5b1004b8f99e5ac4e755874b4a531e3ea484` |

`SHA256SUMS` in this folder is the `sha256sum` output for both files; verify
with `sha256sum -c SHA256SUMS`.

The PDF's screenshots show `WT05-V1.0.011b.bin` on a **Bora 420 H** — the
manual is one version older than the file that was sent with it, and the `H`
suffix is the heater variant. Roth-Kippe has not published a changelog; what
V1.0.012 changes over V1.0.006 is unknown.

## Static analysis of `WT05-V1.0.012.bin` (2026-09-30)

Read-only analysis with `strings`, `file` and a small entropy script. Nothing
was flashed. Layout of the image:

| Offset | Content |
|---|---|
| `0x00000`–`0x3ffff` | Entropy 8.0 bits/byte: **encrypted or compressed MCU code**. No header magic, no readable strings. Not analysable without the vendor's tooling. |
| `0x40000`–~`0x9ffff` | LCD bitmaps (`wt03-2-1.bmp`, `button*.bmp`, `wt_fast/standard/eco.bmp`, `heater.bmp`, `Delay.bmp`, `sperr.bmp`, `numKeypad.bmp`, …), stored as plain data. |
| then | **Web assets in plaintext** — the complete HTTP interface. |
| then | LCD menu strings in DE/FR/IT/EN, and a file-name table listing every web resource. |

### Every file the embedded web server can serve

From the resource table at the end of the image:

```
index.html    index_g.html    index_f.html    index_i.html
status.html   status_g.html   status_f.html   status_i.html
date.html     date_g.html     date_f.html     date_i.html
software.html software_g.html software_f.html software_i.html
wifi.html     wifi_g.html     wifi_f.html     wifi_i.html
lcd.html      info.html
menu.png      refresh.png     favicon.ico     language.bin
```

Plus three dynamic paths referenced from the templates:

- `LCD.BMP?<cache-buster>` — the live screen image (used by `lcd.html`, and
  by this integration's camera entity).
- `log-<title>-<device-id>-<version>.bin` — **"Download Log"** link on
  `status.html`. Binary, format unknown. The device menu strings contain
  *"Log connecter" / "Effacer LOG"* (FR), so the dryer keeps an on-device log
  that can be enabled and cleared from the display. Worth probing on the live
  device — it might contain a cycle history.
- `0z.bin` — `POST multipart/form-data` firmware upload from `software.html`
  (already on the probe tool's blocklist).

### Writable endpoints

Exactly three, all already known:

| Endpoint | Parameters | Purpose |
|---|---|---|
| `date.html?Z1=<d>&Z2=<m>&Z3=<yy>&P=0&Z4=<HH%3AMM%3ASS>&Z5=Save` | GET | set clock |
| `wifi.html?S0=<ssid>&S1=<password>&es=Save` | GET | WLAN credentials |
| `0z.bin` | POST file | firmware upload |

**There is no program / start / stop / filter-reset endpoint in V1.0.012.**
This confirms Roth-Kippe's August 2026 statement that the LAN interface only
mirrors the display.

### Template variables (`$v…`)

| Variable | Meaning (from page context) |
|---|---|
| `$vT0` | device title, e.g. `Bora 410` (page `<title>` and heading) |
| `$vV0` | software version, e.g. `V1.0.012` |
| `$vV1` | 8-hex device id (also in the AP SSID `Bora 4xx-<id>`) |
| `$vV2` | cache-buster for `LCD.BMP` |
| `$vV3` | extra `info.html` line — the `Filter hh:mm` counter |
| `$vp0` / `$vp1` / `$vp5` | present temperature / RH / operation on `status.html` |
| `$vS0` / `$vS1` | SSID / password on `wifi.html` (plaintext — see the security note in the main README) |

### Impact on the integration

The markers the coordinator parses are unchanged in V1.0.012:
`Present Temperature:`, `Present RH:`, `Present Operation:` on `status.html`;
`V<x.y.z><br>` followed by the 8-hex id, `Bora <model>` and `Filter <h>:<m>`
on `info.html`. Note the vendor typo `Sofware version` on `software.html` —
we do not parse that page. Expect the integration to work unchanged after an
update; this is derived from the image, not yet verified on a live device.

### Things visible in the LCD strings (device menu, not reachable over LAN)

`Servicetechniker` / `Technicien de service` menu, `Werkeinstellungen`
(factory reset), `Sperrzeit` (lock-out window), `Einschaltverzögerung`,
`Mehrfamilienhaus` mode, `Kompressorsteuerung`, `Heizung immer ein/auto/aus`,
`Filter gereinigt` (the filter-reset action), `Ventilator Fehler`,
`Abtauung`/`Abtauwiederherstellung`, `Kalibrierung`. None of these are exposed
by the web interface.
