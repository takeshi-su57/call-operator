# Documentation Rules

How to structure, maintain, and keep documentation in sync with the evolving system.

## Docs Location

Documentation lives in `docs/` at the repo root as simple Markdown files.

```
docs/
├── architecture/
│   ├── architecture.md      <- System architecture overview (living doc)
│   └── adr/                 <- Architecture Decision Records (append-only)
│       └── yyyy-mm-dd-<name>.md
└── guide/
    ├── developer.md         <- Local setup, dev workflow, commands
    └── deployment.md        <- Docker, production, distribution
```

## Architecture Overview (`docs/architecture/architecture.md`)

The living document describing the current system state. Must contain:
- System diagram (ASCII)
- Pipeline flow description
- Component descriptions
- Data flow
- Current limitations

Update in the same PR that changes the architecture.

## Architecture Decision Records (ADRs)

ADRs capture **why** decisions were made. Append-only — never deleted, only superseded.

### File naming
```
docs/architecture/adr/yyyy-mm-dd-<name>.md
```

### Template
```markdown
# <Title>

**Date:** yyyy-mm-dd
**Status:** accepted | superseded by [link] | deprecated

## Context
What problem or situation requires a decision?

## Decision
What did we decide and why?

## Consequences
What are the trade-offs?
```

### When to write an ADR
- Choosing a framework or major dependency
- Changing the pipeline architecture or stage design
- Adding a new adapter or provider integration
- Any decision someone might question later

### When NOT to write an ADR
- Bug fixes, adding test cases, minor refactors

## Guides (`docs/guide/`)

Practical how-to documents:
- `developer.md` — local setup, dev workflow, all commands, troubleshooting
- `deployment.md` — Docker, production, distribution, scaling

Update rules:
- Update `developer.md` when commands, env vars, or dev workflow change
- Update `deployment.md` when Docker, packaging, or deployment changes

## Sync Protocol

### When architecture changes
1. Update `docs/architecture/architecture.md`
2. Write an ADR if significant
3. Update `.claude/CLAUDE.md` Architecture Patterns section
4. Update `README.md` if it affects project structure or commands

### When environment variables change
1. Update `.env.example`
2. Update `config.py`
3. Update `README.md` env vars table
4. Update `docs/guide/developer.md` env vars table

### When commands change
1. Update `README.md` commands section
2. Update `.claude/CLAUDE.md` Key Commands section
3. Update `docs/guide/developer.md` All Commands table

### When dev workflow or setup changes
1. Update `docs/guide/developer.md`
2. Update `README.md` Quick Start section

### When packaging or deployment changes
1. Update `docs/guide/deployment.md`

## Anti-Patterns

- Aspirational docs — describe what IS, not what's planned
- Duplicating content — link instead of copy
- Stale docs — update in the same PR as the code change
