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
| Temperature | sensor | °C, room/intake temperature (optional fallback to an external sensor when the BORA is offline) |
| Humidity | sensor | %, relative humidity measured by the BORA (optional fallback to an external sensor when the BORA is offline) |
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

- **v0.7.0** — Filter maintenance now surfaces as a **persistent notification**
  (the notification panel) instead of a repair issue under Settings → System →
  Repairs. A filter reminder is real-world appliance maintenance, not a Home
  Assistant health problem, so the notification panel is the idiomatic channel
  (this mirrors how the Dreame vacuum integration handles consumables). The
  notification self-clears once the filter is reset on the device, and can be
  turned off with the new *Show filter maintenance notification* option.
  Dismissing the notification acknowledges the reminder — it stays gone until
  the filter is reset on the device and the counter climbs over the threshold
  again, so it does not re-nag on every poll. (The counter itself can only be
  reset on the device display; the BORA exposes no LAN endpoint for it.) Any
  leftover repair issue from earlier versions is removed automatically on
  upgrade.
- **v0.6.0** — Optional temperature and humidity fallback sensors. Pick an
  external temperature and/or humidity sensor in the integration's options
  and the BORA's `Temperature` / `Humidity` entities keep reporting from
  that source while the BORA itself is offline. When the BORA is online,
  its own readings are still used.
- **v0.5.1** — When the device is unreachable, `Operation` reports `Off`
  and `Drying` reports `false` instead of freezing on the last live value.
  This avoids stuck `Drying` readings when the user cuts power mid-cycle.
  Filter sensors and firmware version still retain their last value (those
  remain factually correct when offline).
- **v0.5.0** — Filter, firmware, operation and drying sensors retain their
  last successful value while the device is unreachable, instead of going
  `unavailable`. Temperature and humidity still go `unavailable`, since a
  stale reading would be misleading. Closes
  [#2](https://github.com/chriguschneider/hass-bora-dryer/issues/2).
- **v0.4.0** — Built-in filter-maintenance reminder when filter operating
  hours exceed the configured threshold; it clears automatically once the
  filter is reset on the device. Removes the need for an external YAML
  automation to surface filter maintenance. (Originally a repair issue;
  changed to a persistent notification in v0.7.0.)
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
