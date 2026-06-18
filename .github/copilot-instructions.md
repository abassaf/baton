# Copilot instructions - baton

This repo packages `baton`, a skill for handing off in-progress agent work
between sessions, models, and machines. The skill lives at `skills/baton/` (see
`skills/baton/SKILL.md`); the script is `skills/baton/baton.py` (Python 3, no
dependencies).

When the user asks to hand off, save, checkpoint, or carry over the current
session - however they phrase it ("pass the baton", "give me a handoff prompt",
"I'm about to hit the context limit", "save this session", "archive this
conversation", "continue on another machine", "get another model to verify
this") - run the baton workflow. Match intent, not exact wording. If a request
is genuinely ambiguous (bare "save this", "wrap up"), ask one short yes/no
question first.

Workflow:

1. `python3 skills/baton/baton.py new "short-slug"` - scaffolds
   `handoff/NNN-short-slug/` with `STATE.md`, `CONTINUE.md`, and a reconstructed
   `transcript.md`, and gitignores `handoff/`. Copilot CLI sessions are
   auto-detected at `~/.copilot/session-state/*/events.jsonl`; otherwise pass
   `--source PATH` or set `BATON_SOURCE`.
2. Fill in `STATE.md` (objective, locked decisions, done, outstanding, landmines,
   environment) for an agent with no memory of the session.
3. Fill in `CONTINUE.md` (pick one target: VERIFY / IMPLEMENT / RESUME; set repo
   and branch).
4. Report the folder path, the chosen target, and whether a transcript was
   captured.
