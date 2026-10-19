# Architecture Decision Records

Short, dated records of decisions that shape this repo. They exist so a
later change (human or AI) does not silently undo a deliberate call.

## When to write one

Write an ADR when a change:

- adds a **new upstream endpoint, dataset, host or runtime dependency**,
- changes a **budget** (request cadence, traffic, bundle size, ...),
- adds a **platform**, a **public config/option key** or a public API,
- adds or moves a **quality gate** (a CI job, a lint rule, a coverage
  floor),
- introduces a **new architectural pattern** or breaks a module boundary,
- **deviates from an existing accepted ADR**.

Skip it for bug fixes that keep the contract, refactors inside a module,
added test coverage, and prose/style tweaks.

## How

1. Copy [`template.md`](template.md) to `NNNN-short-slug.md` (next free
   number).
2. Fill in Context, Decision, Consequences. Keep it to a screen.
3. Land it in the same PR as the code it describes, and add it to the
   index below.

## Changing an accepted ADR

Do not rewrite it. Append a section and keep the original text:

```
## Amendment YYYY-MM-DD (#issue)

What changed and why. Decided by: <owner | ADR-NNNN>.
```

A decision that reverses the ADR gets a new ADR, and the old one's status
becomes `Superseded by ADR-NNNN`.

## Index

- [0001 — Quality gates, release process and agent automation from repo-standard](0001-quality-gates-and-agent-automation.md)
- [0002 — Read the BORA through its local HTTP status pages, read-only](0002-local-http-status-pages.md)
