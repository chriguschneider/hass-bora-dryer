---
name: documentation-guardian
description: Proactively suggests an ADR when an architectural change happens in the Bora Dryer repo, and checks planned changes against existing decisions in docs/adr/. Activate on a new upstream endpoint or dependency, a changed budget, a new platform or public option, a new quality gate or CI job, or a deviation from an accepted ADR.
---

# Documentation Guardian

Keeps `docs/adr/` in sync with the code. Two jobs: detect ADR-worthy
changes as they happen and propose drafting one, and check in-progress
changes against existing decisions before they land.

ADR conventions live in [`docs/adr/README.md`](../../../docs/adr/README.md).
When the two disagree, that file wins.

## Activation triggers

- A **new upstream endpoint, host or runtime dependency**.
- A change to a **budget** (request cadence, traffic, bundle size).
- A **new quality gate**: a CI job under `.github/workflows/`, a lint rule
  promoted, a coverage floor, a new required check — ADR-0001.
- A **new platform** or a **new public config/option key** (hard to remove).
- A **pattern deviation** from an accepted ADR.
- The **same logic in a second language or place** (a parser in Python and
  in JS, a table in code and in docs): propose one written spec plus a
  shared golden-fixture test both sides run.

## Skip

- Bug fixes that keep the contract (no new option, boundary, or gate).
- Refactors inside a module with an identical public surface.
- Added test coverage, lint-warning cleanup, prose/style tweaks.

## Workflow

1. When a trigger fires, name the decision and which existing ADR it
   touches (or that it is new).
2. If it deviates from an accepted ADR, say so and stop for the user.
3. If it is a genuinely new decision, offer to draft an ADR from
   `docs/adr/template.md` with the next free number, and land it in the
   same PR as the code.
4. Keep proposals rare and load-bearing: an ADR per bug fix is noise.
