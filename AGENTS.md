# AGENTS.md

Instructions for AI agents (and humans) working in this repo. For what the project is and how to run it, read [README.md](README.md).

## Rule 1: log every change in `changes.log`

Every change to this repo is recorded in [changes.log](changes.log). This covers code, docs, config, tests, git remotes, dependencies and file moves or deletions. Do not make a change without adding an entry.

- **Append only.** Add new entries at the bottom. Never rewrite or delete old entries. If an entry was wrong, add a new entry that corrects it.
- **One entry per logical change**, written when the change is made, not at the end of the session.
- **Entry format** (one block per entry, blocks separated by a blank line):

  ```
  [YYYY-MM-DD] <type>: <short summary>
    files: <comma-separated paths, or "n/a">
    why:   <reason for the change>
    notes: <optional: follow-ups, known problems, how it was verified>
  ```

- **Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `config`, `git`.
- Use the real date and real paths. Do not log things that did not happen. If something was tried but not finished, say so in `notes`.
- When you commit, you may add the short commit hash to `notes`.

## Rule 2: keep the docs in step

- If a change alters behaviour, controls, levels, or the project layout, update [README.md](README.md) in the same change, and log both.
- If you find a problem you are not fixing now, add it to "Known issues" in the README and mention it in `notes`.

## Rule 3: confirm before outward-facing git actions

Do not commit, push, force-push or change remotes without the owner asking. Local, reversible work (editing files, running tests) is fine.

## Conventions

- Python 3.12+, run with `uv`. Lint with `uv run ruff check .` and test with `uv run pytest`.
- The code style is compact on purpose (one-line statements, `s` as the self name, line length 160). Match the surrounding code rather than reformatting it.
- No image assets: all art is drawn in code.
- `tests/golden_baseline.json` is a recorded baseline. Change it only for an intended gameplay change, and log why.
- Do not commit `rogue_settings.json`, `.venv/`, `qa/shots/` or caches (already in `.gitignore`).
