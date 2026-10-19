---
name: Bug report
about: Report a problem
title: ''
labels: bug
assignees: ''

---

## Describe the bug

A clear and concise description of what the bug is.

## To reproduce

1. ...
2. ...
3. See error

## Expected behavior

What you expected to happen.

## Logs

Relevant lines from Settings → System → Logs (filter for `bora_dryer`).
For more detail, enable debug logging first: Settings → Devices & services →
BORA Raumluft-Wäschetrockner → ⋮ → *Enable debug logging*, reproduce the
problem, then disable it again (the log file downloads).

## Environment

- **Home Assistant version**: (e.g., 2026.10.0)
- **Integration version**: (e.g., 0.8.1)
- **BORA model and firmware**: (e.g., BORA 410, V1.0.006; shown on
  `http://<bora-ip>/info.html`)
- If values are missing or wrong: the contents of `http://<bora-ip>/info.html`
  and `status.html`. **Never** paste `wifi.html`: it shows your WLAN password
  in plaintext.

## Additional context

Anything else that helps.
