# AGENTS.md

Conventions for AI-assisted contributions to this repo (Claude Code,
Cursor, Codex, Aider, or any other assistant). Read this first if you are
an AI assistant working on a branch, or a human driving one.

---

## Shared Skeleton

These conventions apply across all of chriguschneider's repos and come from
[`repo-standard`](https://github.com/chriguschneider/repo-standard). Repo-specific sections follow below.

### Commit attribution

Commits made with AI assistance carry a `Co-Authored-By:` trailer that
names the tool and model honestly, e.g.:

```
Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Codex <noreply@openai.com>
```

The exact string is not load-bearing; what matters is that git history
reflects what did the typing.

### Language

English only in code, comments, commit messages, and these repo docs.
Non-English is fine in chat, but never gets persisted to a file or a
commit.

### Comment discipline

Inline comments earn their place by explaining the *why* (a hidden
constraint, a subtle invariant, a workaround), not by restating the
code. The PR description is the place for context that does not survive
the diff.

### Model selection

Route the model to the difficulty, not the other way round:

- **Haiku** — trivial mechanical: typos, docs, a config default, a bumped
  constant, value validation.
- **Sonnet** — the default: normal bug fixes, tests, CI, well-scoped
  features.
- **Opus** — architectural surface: lifecycle/teardown, concurrency,
  hardening, ambiguous root-cause hunting, anything ADR-worthy.

### Parallel work

- **Branch naming**: `<tool-or-initials>/<issue>-<slug>`, e.g.
  `claude/4-config-flow`.
- **Issue claiming**: `gh issue edit <N> --add-assignee @me` before
  starting, so parallel contributors (and the autopilot) see it is taken.
- **Worktrees**: parallelize along module boundaries, one worktree each:
  `git worktree add ../hass-bora-dryer-<issue> <branch>`. One file, one lane.

### Draft PRs

CI runs on every push. If you iterate with several pushes, open the PR as
a **draft** until you expect CI to pass, then mark ready. Direct push to
`master` is not the flow; open a PR.

### Changelog entries

Every PR that changes user-visible behavior adds an entry to
`CHANGELOG.md` under `## [Unreleased]` in the right subsection
(Added/Changed/Deprecated/Removed/Fixed/Security, per
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/)).

**Exemption:** a fix for a feature that never appeared in a released
version needs no entry — it has no user-visible before-state.

Write entries for users: would they click *Update* because of this line?
HACS and release pages show the section as is. Internal work (refactors,
CI, tests) goes in a short *Under the hood* list at the end of the section,
or nowhere.

The release commit (`chore(release): vX.Y.Z`) renames `## [Unreleased]`
to `## [vX.Y.Z] — YYYY-MM-DD`; the release workflow extracts that section
verbatim as the GitHub release notes.

### Generated files and data

- A committed build output (bundle, generated table, PDF) has a CI check
  that it matches its sources, and is regenerated in the same commit as
  the source change. On a rebase conflict, regenerate; never hand-merge it.
- Test fixtures are trimmed real files (keep the real header, encoding and
  a handful of rows), never hand-written. `tests/README.md` says where each
  one was cut from.
- Domain data (lookup tables, codes, thresholds) cites its source:
  `docs/upstream.md`, a URL or a fixture. Nothing is invented.

### Architectural decisions

If a change adds an upstream endpoint or dependency, adds a platform or a
public option, adds a quality gate, or deviates from an existing ADR, it
needs an ADR. Triggers and the template are in
[`docs/adr/README.md`](docs/adr/README.md). Land the ADR with the code.

Claude Code users get automatic prompts via the repo-local skills in
`.claude/skills/`:

- **`commit-guardian`** — before any `git commit`, checks the staged diff
  against accepted ADRs and these conventions. Non-blocking.
- **`documentation-guardian`** — proposes an ADR when an architectural
  change happens and flags changes that contradict an existing decision.

### Automation

Opt-in, draft-PR-only (see [`docs/agent-automation.md`](docs/agent-automation.md)):
add the **`agent:go`** label to hand an issue to Claude, or write
**@claude** in a comment (owner/collaborators only). The model comes from
the issue's labels via `.github/scripts/pick-model.sh`. Unattended runs
use a tool allowlist, cannot write to `.github/` or `.claude/` (path guard
hook), and only act on issue text from people with write access.

---

## Repo-Specific: BORA dryer

### What this is

A local-polling Home Assistant custom integration (HACS) for the
Roth-Kippe **BORA 4xx** room-air laundry dryer. It polls the dryer's
built-in, unauthenticated WLAN status pages every 60 s and turns them into
entities under one device: operation, drying, temperature, humidity,
filter wear, firmware, an LCD mirror (camera), a set-clock button, and
optional wrappers around a smart plug in front of the dryer.

It is deliberately **not** a remote control: the device offers none (see
the README, *What it does not do*). It is not a cloud integration, needs
no account, and does not talk to any vendor server. `tools/` and
`firmware/` hold reverse-engineering notes and scripts for developers;
they are not part of the integration and never ship.

### Repo structure

```
custom_components/bora_dryer/
├── __init__.py          # entry setup/unload (succeeds while the device is off),
│                        # removes the pre-v0.7.0 repair issue
├── coordinator.py       # polls status.html + info.html, regex parser,
│                        # filter reminder (persistent notification)
├── config_flow.py       # host -> probe info.html -> unique id = device id;
│                        # options flow (smart plug, fallbacks, filter)
├── entity.py            # device info, via_device = the smart plug's device
├── sensor.py            # status sensors, fallback + mirror sensors
├── binary_sensor.py     # drying, filter due
├── camera.py            # LCD.BMP -> PNG (Pillow, in the executor)
├── button.py            # set clock (date.html), the only write
├── switch.py            # wraps the configured smart-plug switch
├── const.py             # DOMAIN, VERSION, constants
├── brand/               # icon.png, logo.png
├── strings.json / translations/
└── manifest.json
tests/                   # pytest + pytest-homeassistant-custom-component
├── fixtures/            # device pages (tests/README.md: source of each)
└── README.md            # fixture inventory and TODOs
tools/                   # developer-only probe / log-capture scripts (not shipped)
firmware/                # provenance + static analysis of vendor firmware
                         # (binaries are gitignored, never committed)
docs/adr/                # decisions
docs/upstream.md         # what is known about the device's HTTP interface
```

Not there yet, compared with `repo-standard` (each needs its own issue,
never a drive-by change): `diagnostics.py`, a `client.py` without Home
Assistant imports (the parser lives in `coordinator.py`, the probe in
`config_flow.py`, and both duplicate `RE_DEVICE_ID` / `RE_MODEL`: change
them together), and `entry.runtime_data` instead of `hass.data[DOMAIN]`.

### Non-negotiables

The agent workflows tell the agent to stop rather than break one of these.

- **Read-only towards the dryer** ([ADR-0002](docs/adr/0002-local-http-status-pages.md)).
  The integration sends only `GET` to `status.html`, `info.html`,
  `LCD.BMP?<n>`, and `date.html?…&Z5=Save` from the *Set clock* button press.
  Never request `wifi.html` (it shows the WLAN password in plaintext), never
  `software.html` or the `0z.bin` firmware upload, and never write anything
  else. A new endpoint needs an ADR first.
- **No control that the device does not have.** The BORA cannot be
  started, stopped, given a program or have its filter counter reset over
  the network (README, *What it does not do*; `firmware/README.md`,
  *Writable endpoints*). Do not add entities that suggest otherwise. The
  `Power` switch toggles the user's smart plug, never the dryer.
- **Security note from the README.** The web interface has no
  authentication. Nothing the integration logs, stores or (later) puts into
  diagnostics may contain the WLAN SSID or password, and no text asks users
  to share `wifi.html`.
- **Everything local.** No cloud service, account, telemetry or vendor
  server; the only network peer is the dryer on the configured host.
- **Identity is stable.** The config entry's unique id is the 8-hex device
  id from `info.html` (the host only when none was parsed), and entity
  unique ids are `<unique id>_<key>`. Users build automations on them:
  changing either needs an ADR and a migration.
- **Offline is normal** (CHANGELOG v0.3.2, v0.5.x, v0.8.0). Setup succeeds
  while the dryer is off; state-like entities report `Off` / not drying,
  others hold and restore their last value; the Display stays available.
  `tests/test_device_offline.py` pins this.
- **Facts about the device cite their source**: `docs/upstream.md`,
  `firmware/README.md` or a fixture with its row in `tests/README.md`.
  Never claim a firmware was tested live when it was only read statically
  (V1.0.012 so far).

### Reverse-engineering hygiene (`tools/`, `firmware/`)

- `tools/` scripts stay **read-only** by construction: `probe_endpoints.py`
  sends everything through `safe_request()` with the hard-coded blocklist
  (`Z5=Save`, `0z.bin`) and the method whitelist; `log_capture.py` through
  `get()`, which allows `GET` on `status.html`, `info.html` and
  `log-*.bin` only. Never weaken those chokepoints or add a second request
  path around them.
- Their output (`tools/probe_results/`, `tools/log_capture_results/`) is
  gitignored and may contain the WLAN password and device fingerprints:
  never commit it, never paste raw output into an issue, PR or chat.
- **Firmware binaries and the vendor PDF are never committed**
  (`firmware/*.bin`, `firmware/*.pdf` are gitignored; we may not
  redistribute them). `firmware/` keeps only provenance, `SHA256SUMS` and
  static-analysis notes. Nothing is ever flashed or uploaded by a script
  or an agent.
- Neither folder ships: the release zip contains only
  `custom_components/bora_dryer/`. A PR touching `tools/` or `firmware/`
  is always held for a human by the reviewer.

### Release procedure

Releases are automated via tag push (`.github/workflows/release.yml`, ADR-0001):

1. **Update version and changelog**: bump `version` in
   `custom_components/bora_dryer/manifest.json` and `VERSION` in
   `const.py`. Rename `## [Unreleased]` to `## [vX.Y.Z] — YYYY-MM-DD`,
   add a fresh empty `## [Unreleased]` and the link definition. Commit as
   `chore(release): vX.Y.Z`.
2. **Verify**: `pytest -q tests/test_metadata.py tests/test_changelog.py`.
3. **Tag** with an **annotated** tag whose message is the release title:
   `git tag -a vX.Y.Z -m "what changed"`.
4. **Push**: `git push origin vX.Y.Z`. The workflow verifies the tag
   against the manifest, extracts the notes, packages `bora_dryer.zip`
   and creates the release. HACS reads it.

### Testing

- `pip install -r requirements_test.txt` once.
- **Lint**: `ruff check custom_components tests`.
- **Tests**: `pytest -q`. Metadata/changelog tests are stdlib-only;
  integration tests use `pytest-homeassistant-custom-component`
  (`hass` fixture, `enable_custom_integrations`). The device never answers
  for real: `aioclient_mock` replays the pages in `tests/fixtures/`
  (`mock_device`, `switch_device` in `tests/conftest.py`). Never hit the
  network in tests. `tests/README.md` says where each fixture comes from;
  the current page fixtures are marker-only stand-ins until real captures
  replace them.
- **New behavior gets a test**: a config-flow field gets a flow test, a
  new parsed field gets a coordinator test against a fixture, offline
  behaviour gets a `test_device_offline.py` case.

### Home Assistant pitfalls

Lessons from real integrations; several shipped with every test green.

- **`vol.Required` with an empty-string default blocks the form.** The UI
  treats `""` as "not filled in" and refuses to submit, while a test that
  calls `async_configure` with a value passes. Use `vol.Optional` for
  fields that may stay empty, or a real default; give a required field no
  default at all.
- **Open cards only see what the coordinator announces.** Data that
  changes outside `_async_update_data` must go through
  `coordinator.async_set_updated_data(...)` or
  `coordinator.async_update_listeners()`.
- **Availability follows the data, not the last poll.** One failed poll
  must not blank every card; here the `survives_offline` /
  `offline_value` descriptions decide explicitly per entity.
- **Never block the event loop.** No synchronous I/O and no heavy parsing
  on the loop; the BMP → PNG conversion already runs in
  `hass.async_add_executor_job`.
- **Diagnostics redact secrets and location.** When `diagnostics.py` is
  added, everything goes through `async_redact_data` with the host and the
  device id in `TO_REDACT`, and a test proves it.
- **The BORA's HTTP/1.0 server is fragile.** It drops connections under
  fast pacing and starves while drying (`tools/README.md`,
  `tools/probe_endpoints.py`). Do not add requests per poll or shorten the
  60 s interval / 8 s timeout without an ADR.
