# Skill: Write ADR

Create an Architecture Decision Record when a significant architectural decision is made.

## When to Use

- Choosing a framework or major dependency
- Changing the agent flow or graph structure
- Adding a new tool or integration
- Changing deployment or storage strategy
- Any decision someone might question later

## Steps

1. Determine the date and a short kebab-case name
2. Create `docs/architecture/adr/yyyy-mm-dd-<name>.md` using the template
3. Update `docs/architecture/architecture.md` if the decision changes the current architecture
4. Follow sync protocol in `.claude/rules/ai-framework.md` for any `.claude/` file updates

## Reference

- See `templates/adr-template.md` for the file format
- See `examples/` for worked examples
- See `.claude/rules/documentation.md` for when to write (and when not to write) an ADR
