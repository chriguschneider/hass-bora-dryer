# Tests

## How to run

```
pip install -r requirements_test.txt
ruff check custom_components tests
pytest -q
```

Integration tests use `pytest-homeassistant-custom-component` (`hass`
fixture). The dryer never answers for real: `aioclient_mock` replaces the
shared aiohttp session, and `tests/conftest.py` registers the fixture pages
under a TEST-NET host (`mock_device`; `switch_device(True/False, …)` to
switch the device on, off, or serve other page bodies).

| File | Covers |
|---|---|
| `test_config_flow.py` | create, blank name, same device id updates the host and aborts, cannot connect (and recovers), HTTP error, not a BORA, second device, lower-cased id, host fallback without an id |
| `test_coordinator.py` | every parsed field, negative temperature, pages without markers, unreachable device, filter reminder (rising edge, dismiss, reset, options) |
| `test_init.py` | setup/unload, removal of the pre-v0.7.0 repair issue, options flow and reload |
| `test_entities.py` | entity states, device info, set-clock request, camera BMP → PNG, smart-plug switch and mirror sensors |
| `test_device_offline.py` | setup while off, values held when the device goes off, restore after a restart, fallback sensors, no camera image while off |
| `test_metadata.py`, `test_changelog.py` | version sync, manifest/hacs.json keys, translations, zip release wiring, changelog sections and links |

## Fixtures

The standard is: fixtures are **trimmed real files**, never hand-written
(keep the real structure, encoding and quirks; under ~50 KB; one row per
file below).

**The repo contains no captured device response** (checked 2026-10-19: no
page dumps in `tools/`, `firmware/`, `docs/` or the git history; the
capture tools write to gitignored folders). The two page fixtures are
therefore **synthetic, marker-only stand-ins**: each contains only the
markers the parser reads, in the shape documented in the repo, and nothing
else. They test the parser and the entities against that documented shape;
they do **not** prove that real pages parse (surrounding HTML, encoding,
whitespace, extra lines that might also match).

| Fixture | Source | Date | What it contains |
|---|---|---|---|
| `status.html` | **Synthetic.** Markers from `firmware/README.md` (*Impact on the integration*; template variables `$vp0`, `$vp1`, `$vp5`) and the regexes `RE_TEMPERATURE`, `RE_HUMIDITY`, `RE_OPERATION` in `coordinator.py`; operation text `Standby` from the README entity table. Values (21.5 °C, 48 %) are test values. | 2026-10-19 | page title `Bora 410`, `Present Temperature: 21.5 °C<br>`, `Present RH: 48 %<br>`, `Present Operation: Standby<br>` |
| `info.html` | **Synthetic.** Markers from `firmware/README.md` (*Impact on the integration*: "`V<x.y.z><br>` followed by the 8-hex id, `Bora <model>` and `Filter <h>:<m>`"; `$vT0`, `$vV0`, `$vV1`, `$vV3`) and the regexes in `coordinator.py` / `config_flow.py`; model and firmware from the README (*Supported models*: BORA 410, V1.0.006). The id `0a1b2c3d` and the counter `123:45` are test values. | 2026-10-19 | page title `Bora 410`, `V1.0.006<br>`, `0a1b2c3d<br>`, `Bora 410<br>`, `Filter 123:45<br>` |

The LCD bitmap in `test_entities.py` is generated with Pillow in the test:
the camera only converts *a* BMP to PNG, so no device capture is implied.

### TODO (owner): replace the stand-ins with real captures

1. With the dryer on and idle, save the raw bytes (no re-encoding) of
   `http://<bora-ip>/status.html` and `http://<bora-ip>/info.html`, e.g.
   `curl -s http://<bora-ip>/status.html -o status.html`. **Do not** save
   `wifi.html`.
2. Trim them: keep the real HTML structure, encoding and every line the
   regexes could match; replace the 8-hex device id with `0a1b2c3d` (it is
   also part of the access-point SSID), or update `DEVICE_ID` in
   `tests/conftest.py`.
3. Update the values the tests expect (`EXPECTED` in `test_coordinator.py`,
   the parametrised states in `test_entities.py`) to the captured ones, and
   replace the two rows above with endpoint, firmware, date and what was
   kept.
4. Worth capturing too: `status.html` while drying (the exact operation
   text), and, on V1.0.012, both pages to confirm the static analysis.
