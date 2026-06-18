# AGENTS.md

This repo is `baton`, a skill for handing off in-progress agent work between
sessions, models, and machines. This file is the entry point for agents that
read `AGENTS.md` (Codex CLI, and other AGENTS-aware tools).

## When to act as baton

If the user asks to hand off, save, checkpoint, or carry over the current
session - phrased any way, e.g. "pass the baton", "give me a handoff prompt",
"I'm about to hit the context limit", "save this session", "archive this
conversation", "continue this on another machine", "get another model to verify
this" - use the baton workflow below. Match intent, not exact words.

If the request is genuinely ambiguous (e.g. bare "save this", "wrap up"), ask one
short yes/no question before running anything.

## Workflow

1. Scaffold the package:

   ```bash
   python3 baton.py new "short-slug"
   ```

   This creates `handoff/NNN-short-slug/` with `STATE.md`, `CONTINUE.md`, and
   (when it can find the session log) `transcript.md`, and gitignores `handoff/`.
   Codex sessions are auto-detected at `~/.codex/sessions/**/rollout-*.jsonl`. If
   detection misses, pass `--source /path/to/session.jsonl` or set `BATON_SOURCE`.

2. Fill in `STATE.md`: objective, decisions locked (do not relitigate), what is
   done, what is outstanding (priority order), landmines, and environment
   (branch/worktree, how to run and test, required env vars, anything running
   that must not be killed). Write it for an agent with no memory of this session.

3. Fill in `CONTINUE.md`: pick one target - VERIFY (a stronger model checks the
   work), IMPLEMENT (a cheaper model builds the approved items), or RESUME (same
   task, new session/machine) - set the repo and branch, and keep the final
   "restate the plan back to me first" step.

4. Tell the user the folder path, the target you chose, and whether a transcript
   was captured. If they wanted something to paste elsewhere, hand them the
   contents of `CONTINUE.md`.

See `SKILL.md` for the full description.
