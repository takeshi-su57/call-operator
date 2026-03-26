# ADR Template

File: `docs/architecture/adr/yyyy-mm-dd-<name>.md`

```markdown
# <Title>

**Date:** yyyy-mm-dd
**Status:** accepted | superseded by [link] | deprecated

## Context

What is the problem or situation that requires a decision?

## Decision

What did we decide and why?

## Consequences

What are the trade-offs? What becomes easier? What becomes harder?
```

## Naming

- Date: `yyyy-mm-dd` of when the decision was made
- Name: kebab-case, concise description of the decision
- Examples:
  - `2026-03-25-langgraph-agent-framework.md`
  - `2026-03-25-playwright-browser-automation.md`
  - `2026-04-01-add-checkpointing.md`

## Status Values

- **accepted** — active decision
- **superseded by [link]** — replaced by a newer ADR (link to it)
- **deprecated** — no longer relevant (e.g., feature removed)
