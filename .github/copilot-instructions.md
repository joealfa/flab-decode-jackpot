# Copilot instructions

Use [AGENTS.md](../AGENTS.md) for the current project architecture, conventions,
and development commands. Treat the implementation and `pyproject.toml` as the
source of truth; older documentation has been consolidated.

- Use `uv` for Python dependencies and commands.
- Inspect nearby code and preserve unrelated worktree changes.
- Keep changes focused; validate inputs and use existing storage and security
  helpers.
- Add or update tests for behavior changes, and run the relevant checks from
  `AGENTS.md`.
- Keep comments concise and only for non-obvious intent.
- Never describe lottery patterns as a way to predict or improve winning odds.
