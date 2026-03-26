# AI Framework Maintenance Rules

How to maintain and evolve the AI engineering framework (`.claude/`, `AI_ENGINEERING.md`).

## Framework File Hierarchy

```
AI_ENGINEERING.md              <- Human-readable overview
.claude/
├── CLAUDE.md                  <- AI context (auto-loaded, < 200 lines)
├── rules/                     <- Detailed guidance documents
│   └── <topic>.md
├── skills/                    <- Reusable task patterns
│   └── <skill-name>/
│       ├── skill.md
│       ├── templates/
│       └── examples/
└── settings.local.json        <- Claude Code permissions
```

## Sync Protocol

### When architecture changes (new pipeline stage, adapter, or provider)
1. Update `.claude/rules/architecture.md`
2. Update `.claude/CLAUDE.md` — Architecture Patterns + Pipeline Flow
3. Update `AI_ENGINEERING.md` — Core Principles section
4. Update `README.md` — if project structure or commands change
5. Update `docs/architecture/architecture.md` — system diagram

### When adding a new adapter
1. Create `src/call_operator/adapters/<platform>.py`
2. Implement the `MeetingAdapter` interface from `adapters/base.py`
3. Update `.claude/CLAUDE.md` — Repository Layout
4. Update `docs/architecture/architecture.md` — supported platforms

### When adding a new STT/TTS provider
1. Create `src/call_operator/stt/<provider>.py` or `tts/<provider>.py`
2. Implement the abstract base class from `stt/base.py` or `tts/base.py`
3. Register in the factory function (`get_stt()` or `get_tts()`)
4. Update `.claude/CLAUDE.md` — Repository Layout
5. Update `.env.example` with provider-specific env vars

### When environment variables change
1. Update `.env.example`
2. Update `src/call_operator/config.py` — Settings class
3. Update `README.md` — env vars table

### When adding a new rule
1. Create `.claude/rules/<topic>.md`
2. Add reference in `.claude/CLAUDE.md` under Rules section
3. Add row in `AI_ENGINEERING.md` Framework Structure table

### When adding a new skill
1. Create `.claude/skills/<skill-name>/` with `skill.md`, `templates/`, `examples/`
2. Add row in `AI_ENGINEERING.md` Framework Structure table

## Post-Implementation Checklist

After completing any implementation task, verify:

### Files to check
- [ ] `.claude/CLAUDE.md` — Tech Stack, Repository Layout, Architecture Patterns, Key Commands, Known Gaps
- [ ] `README.md` — project structure, commands, env vars
- [ ] `docs/architecture/architecture.md` — if architecture changed
- [ ] Write ADR if it's a significant decision

### Quality checks
```bash
ruff check src/ tests/     # Lint
ruff format src/ tests/    # Format
mypy src/                  # Type check
pytest                     # Tests
```

## CLAUDE.md Principles

- **Under 200 lines** — bloating degrades AI performance
- **An index, not a manual** — summarize, point to rules for details
- **Factual, not aspirational** — describe what IS, not what should be
- **No duplicated content** — if it's in a rule file, don't repeat it

## Rule Design Principles

- Reference real code in this codebase, not generic advice
- Show concrete examples from existing code
- State anti-patterns explicitly ("do NOT")
- Stay current — outdated rules are worse than no rules
- One topic per file

## Skill Design Principles

- Solve a repeatable task done more than once
- Templates use `.md` files with `{placeholder}` markers
- Examples show a complete worked scenario
- Include what to import and from where
