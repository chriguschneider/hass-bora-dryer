# Home Assistant integration for Roth-Kippe BORA dryers

A local-polling Home Assistant integration for the **Roth-Kippe BORA 4xx**
[Raumluft-Wäschetrockner](https://www.roth-kippe.ch/waeschetrockner) (Swiss-made
heat-pump room-air laundry dryers). Tested against BORA 410 firmware V1.0.006.

The BORA exposes a small read-only HTTP status interface on its WLAN. This
integration scrapes that interface and surfaces the values as proper Home
Assistant entities, grouped under a single device.

## Entities

| Entity | Type | Notes |
|---|---|---|
| Temperature | sensor | °C, room/intake temperature |
| Humidity | sensor | %, relative humidity measured by the BORA |
| Operation | sensor | text: `Standby`, `Washing Drying`, ... |
| Filter operating hours | sensor | hours since last filter reset |
| Firmware version | sensor (diagnostic) | e.g. `V1.0.006` |
| Drying | binary_sensor | on while the operation state contains `Drying` |
| Filter maintenance due | binary_sensor | on when filter hours ≥ 280 (manufacturer warns at 300) |

## What it does NOT do

The BORA web interface offers **no remote control** — no on/off, no program
selection, no parameter changes. The manufacturer designed the WLAN interface
purely as a status mirror. To switch the dryer on/off remotely you still need a
smart plug (e.g. a Shelly PM in front of the dryer).

## Install

1. Add this repository as a custom HACS repository:
   - Open HACS → ⋮ → **Custom repositories**
   - URL: `https://github.com/chriguschneider/hass-bora-dryer`
   - Category: `Integration`
2. Install **BORA Raumluft-Wäschetrockner** from HACS and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → BORA
   Raumluft-Wäschetrockner** and enter the IP address of your BORA.

## Polling

The integration polls `/status.html` and `/info.html` every 60 seconds. The
BORA's HTTP server is unauthenticated and HTTP/1.0 — keep it on a trusted LAN
(see security note below).

## Security note

⚠️ The BORA web interface has **no authentication**. Anyone on the same network
can view status, change the device clock, upload firmware, and **read the WLAN
password in plaintext** on the WiFi configuration page. This is a vendor design
choice, not a configuration issue. Recommendation: place the BORA in an
isolated IoT VLAN or restrict LAN access to it.

## Supported models

Likely works with the entire BORA 4xx series (BORA 408 / 410 / 415 / 420),
since they share the same controller. Only tested on BORA 410. If you have
another model, please open an issue with the contents of `/info.html`.

## Changelog

- **v0.4.0** — Built-in filter-maintenance repair issue. The integration
  now raises a Home Assistant repair issue (Settings → Repairs) when filter
  operating hours exceed the configured threshold; it clears automatically
  once the filter is reset on the device. Removes the need for an external
  YAML automation to surface filter maintenance.
- **v0.3.2** — Setup tolerates an offline device (e.g. when the upstream
  Shelly has cut power). Entities are registered with state `unavailable`
  instead of failing to load entirely until the device is reachable. Closes
  [#1](https://github.com/chriguschneider/hass-bora-dryer/issues/1).
- **v0.3.1** — Optional power & energy mirror sensors. Pick the upstream
  Shelly's power and energy entities in the integration's options and they
  appear under the BORA device alongside the existing entities.
- **v0.3.0** — BORA device is shown as *connected via* the upstream power
  switch device (e.g. a Shelly), once that switch is configured in the
  integration's options.
- **v0.2.0** — Live LCD camera, set-clock button, options flow with
  power-switch wrapper and configurable filter-due threshold, derived
  filter-remaining and filter-progress sensors.
- **v0.1.0** — Initial release: status sensors, drying & filter-due binary
  sensors.

## License

MIT
