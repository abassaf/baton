# baton

Hand off in-progress agent work between sessions, models, and machines.

Coding agents forget. A context window fills, a rate limit hits, you want a
different model to check the plan or a cheaper one to build it, or you walk to
another machine. Whatever was in the agent's head is gone, and you end up
re-explaining the half-finished work from memory.

baton is a small, zero-dependency skill that captures a session at the point of
handoff and produces a portable package any agent can pick up:

- **STATE.md** - objective, locked decisions, what is done, what is outstanding,
  landmines, and how to run things. Written for an agent with no memory of the
  session.
- **CONTINUE.md** - a paste-ready continuation prompt, targeted at whoever picks
  it up next: a more capable model to *verify*, a cheaper one to *implement*, or
  the same task to *resume* elsewhere.
- **transcript.md** - the conversation, reconstructed from the session log.

It's the companion to [plan-review-hub](https://github.com/abassaf/plan-review-hub):
that decides what gets approved; baton carries approved work across the seams.

## Install

The quickest way is the open [skills](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add abassaf/baton
```

It detects your installed agents and adds baton to each - Claude Code, Codex,
Copilot, Cursor, OpenCode, and 70+ others. Use `-g` for a global install or
`-a <agent>` to target specific ones.

No dependencies beyond Python 3. To wire it up by hand instead, copy
`skills/baton/` into your agent's skills directory (for example
`~/.claude/skills/baton/` or `.claude/skills/baton/`), or just run
`skills/baton/baton.py` directly in any project. The repo also ships `AGENTS.md`
(Codex) and `.github/copilot-instructions.md` (Copilot) at the root.

## Use

Ask your agent in whatever words fit - "pass the baton", "give me a handoff",
"I'm about to hit the limit", "save this session", "archive this conversation",
"checkpoint so I can resume", "carry this over to another model". It matches the
intent, and if a request is ambiguous it confirms with you before running. Then
it runs:

```bash
python3 baton.py new "fix-billing-webhooks"
```

Then it fills in `STATE.md` and `CONTINUE.md` (it has the context; the script
only does the plumbing). You get `handoff/NNN-fix-billing-webhooks/`, gitignored,
ready to paste into the next session.

```bash
python3 baton.py detect   # show where it looks for session state
python3 baton.py list     # list existing handoffs
python3 baton.py new ...   # create a handoff
```

### Provider support

Auto-detects session state for:

- **Claude Code** - `~/.claude/projects/<encoded-cwd>/*.jsonl`
- **Codex CLI** - `~/.codex/sessions/**/rollout-*.jsonl`
- **Copilot CLI** - `~/.copilot/session-state/*/events.jsonl`

For any other tool (OpenCode, etc.), point it at the log with
`--source /path/to/session.jsonl` or set `BATON_SOURCE`. Transcript parsing is
best-effort across formats; if a log can't be parsed or found, baton still
scaffolds the package and you fill `STATE.md` by hand.

## Design

- **Zero dependencies.** Standard library only, runs on whatever already has
  Python.
- **Plain markdown output.** Portable across any model, platform, or machine.
- **Plumbing, not judgement.** The script finds the session, rebuilds the
  transcript, scaffolds the folder, and handles `.gitignore`. It never invents
  decisions it can't know - STATE.md and CONTINUE.md are written by the agent
  that did the work.

## Repo layout

```
skills/baton/        the skill itself (SKILL.md + baton.py)
AGENTS.md            Codex entry point
.github/copilot-instructions.md   Copilot entry point
```

## Licence

MIT. See [LICENSE](LICENSE).
