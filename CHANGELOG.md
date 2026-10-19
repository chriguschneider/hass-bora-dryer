# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Release tags carry a `v` prefix (e.g. `v0.8.1`); the release workflow turns
an annotated tag into a GitHub release using the matching section below as
release notes.

Versions before this file existed were listed in the README. Some of them
were never tagged (v0.1.0, v0.2.0, v0.3.2, v0.4.0, v0.5.0, v0.5.1); their
sections have no link definition below. Dates are those of the version
commits.

## [Unreleased]

### Added

- Diagnostics download (Settings → Devices & services → BORA → ⋮ →
  Download diagnostics) with the parsed values and the last `status.html`
  and `info.html` the dryer returned. Host, device id, IP and MAC addresses
  and WLAN credentials are redacted, so it is safe to attach to an issue.

### Changed

- Releases now ship a `bora_dryer.zip` asset, which HACS downloads instead
  of the source tree. The integration still installs to
  `custom_components/bora_dryer`; existing installs update as usual.

### Under the hood

- Test suite (pytest with the Home Assistant test harness), CI with
  hassfest, HACS validation, ruff and pytest (also weekly), CodeQL,
  Dependabot, a release workflow that checks the tag against the manifest
  and this changelog, and hardened agent workflows.
- The changelog moved from the README into this file.

## [v0.8.1] — 2026-10-19

### Fixed

- The manifest no longer lists `Pillow` in `requirements`. Pillow ships
  with Home Assistant, and hassfest rejects core dependencies in a custom
  integration's manifest. No functional change.

## [v0.8.0] — 2026-10-01

### Changed

- Sensors and binary sensors no longer drop to **unavailable** when the
  device is switched off. They hold their last reading, and — via
  `RestoreEntity` — that value now also survives a **Home Assistant
  restart**, so a cold start with the dryer off still shows the last known
  filter wear, firmware, temperature and humidity instead of a row of
  "unavailable". Note: frozen temperature/humidity show a flat line in
  history until the device is back.
- The `Display` camera stays available (reads as idle rather than
  unavailable) and simply serves no image while the device is offline.

## [v0.7.1] — 2026-08-08

### Changed

- Documentation release, no functional changes: fully redesigned README
  (logo, badges, entity table, device-page screenshot), a petition for an
  open local API (since reworked into the owner interest list on
  [issue #4](https://github.com/chriguschneider/hass-bora-dryer/issues/4)
  after Roth-Kippe entered into dialogue), and a draft for the Home
  Assistant community post.

## [v0.7.0] — 2026-06-06

### Changed

- Filter maintenance now surfaces as a **persistent notification** instead
  of a repair issue under Settings → System → Repairs. A filter reminder is
  real-world appliance maintenance, not a Home Assistant health problem, so
  the notification panel is the idiomatic channel (mirroring how the Dreame
  vacuum integration handles consumables). It self-clears once the filter
  is reset on the device. Dismissing it acknowledges the reminder — it
  stays gone until the counter climbs over the threshold again, so it never
  re-nags on every poll. Any leftover repair issue from earlier versions is
  removed on upgrade.

### Added

- *Show filter maintenance notification* option to turn the reminder off.

## [v0.6.0] — 2026-05-10

### Added

- Optional temperature and humidity fallback sensors. Pick an external
  sensor in the options and the BORA's `Temperature` / `Humidity` entities
  keep reporting from that source while the BORA is offline; its own
  readings are used when it's online.

## [v0.5.1] — 2026-05-01

### Fixed

- When the device is unreachable, `Operation` reports `Off` and `Drying`
  reports `false` instead of freezing on the last value — no more stuck
  `Drying` readings when power is cut mid-cycle. Filter and firmware
  sensors keep their last value (still factually correct when offline).

## [v0.5.0] — 2026-05-01

### Changed

- Filter, firmware, operation and drying sensors retain their last
  successful value while the device is unreachable instead of going
  `unavailable`. Temperature and humidity still go `unavailable`, since a
  stale reading would mislead. Closes
  [#2](https://github.com/chriguschneider/hass-bora-dryer/issues/2).

## [v0.4.0] — 2026-05-01

### Added

- Built-in filter-maintenance reminder when operating hours exceed the
  threshold; clears automatically once the filter is reset. Removes the
  need for an external YAML automation. (Originally a repair issue;
  changed to a persistent notification in v0.7.0.)

## [v0.3.2] — 2026-05-01

### Fixed

- Setup tolerates an offline device; entities register as `unavailable`
  instead of failing to load. Closes
  [#1](https://github.com/chriguschneider/hass-bora-dryer/issues/1).

## [v0.3.1] — 2026-05-01

### Added

- Optional power & energy mirror sensors from the upstream smart plug.

## [v0.3.0] — 2026-05-01

### Added

- BORA device shown as *connected via* the upstream power switch device
  once configured.

## [v0.2.0] — 2026-05-01

### Added

- Live LCD camera, set-clock button, options flow with power-switch
  wrapper and configurable filter-due threshold, derived filter-remaining
  and filter-progress sensors.

## [v0.1.0] — 2026-05-01

### Added

- Initial release: status sensors, drying & filter-due binary sensors.

[Unreleased]: https://github.com/chriguschneider/hass-bora-dryer/compare/v0.8.1...HEAD
[v0.8.1]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.8.1
[v0.8.0]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.8.0
[v0.7.1]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.7.1
[v0.7.0]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.7.0
[v0.6.0]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.6.0
[v0.3.1]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.3.1
[v0.3.0]: https://github.com/chriguschneider/hass-bora-dryer/releases/tag/v0.3.0
