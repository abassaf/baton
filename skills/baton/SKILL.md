---
name: baton
description: Hand off in-progress agent work to a fresh session, a different model, or another machine. Produces a portable handoff package - a STATE.md (objective, locked decisions, what is done, what is outstanding, landmines, environment) plus a paste-ready CONTINUE.md continuation prompt, and reconstructs the session transcript. Use when the user says things like "hand this off", "pass the baton", "I'm about to hit the context limit", "give me a handoff prompt", "continue this on another machine", "carry this over to Opus/Codex/a cheaper model", "checkpoint this so I can resume later", "save this session", "save/store the transcript", "archive this conversation", "save a summary of what we did", "wrap up this session", "snapshot where we're at", or any similar request to capture session state so work can continue elsewhere. When it is genuinely unclear whether the user wants this handoff/save behaviour or something else, ask the user to confirm before running it rather than assuming. Zero dependencies, provider-agnostic.
---

# baton

Passes the baton on in-progress work so it survives a dead context window, a
switch to a different model or provider, or a move to another machine. The
output is plain markdown, so any agent on any platform can pick it up.

`baton.py` handles the plumbing. You (the agent) supply the judgement: only you
know what was decided and what is left, so you write `STATE.md` and `CONTINUE.md`.

## When to use

Trigger on any request to capture the session so the work can continue
elsewhere, phrased however the user likes. All of these mean baton:

- "hand this off", "pass the baton", "give me a handoff prompt / document"
- "I'm about to hit the (context / rate) limit", "we're running out of context"
- "continue this on another machine", "pick this up on my laptop"
- "move / carry this over to Opus / Codex / a cheaper model", "get another
  model to verify this"
- "checkpoint this so I can resume", "snapshot where we're at"
- "save this session", "save / store the transcript", "archive this
  conversation", "save a summary of what we did", "wrap up this session"

Match the intent, not the exact words. If the meaning is clear, run it straight
away - do not make the user spell out the steps.

## When to confirm first

If it is genuinely ambiguous whether the user wants a handoff/save, ask one
short yes/no question before running anything. Confirm rather than assume when,
for example:

- "save this" / "save it" with no clear object - they may mean saving a file
  you were editing, not capturing the session.
- "wrap up" / "finish up" - they may mean completing the actual task, not
  archiving the conversation.
- the request could plausibly mean something else in context (committing code,
  writing docs, exporting data).

When confirming, name what baton would do, e.g. "Do you want me to capture this
session as a handoff package (state + continuation prompt + transcript) so you
can pick it up elsewhere?" If they confirm, proceed. If they clearly want
something else, do that instead and don't run baton.

## Steps

### 1. Scaffold the package

```bash
python3 baton.py new "short-slug"
```

`baton.py` is bundled in this skill's directory, next to this `SKILL.md`. Run it
from here, or pass its full path.

This creates `handoff/NNN-short-slug/` containing `STATE.md`, `CONTINUE.md`, and
(if it can find the session log) `transcript.md`. It also adds `handoff/` to
`.gitignore`. If session state is not auto-detected, point it at the log:

```bash
python3 baton.py new "short-slug" --source /path/to/session.jsonl
# or skip the transcript entirely
python3 baton.py new "short-slug" --no-transcript
```

`python3 baton.py detect` shows where it looked. Auto-detection covers Claude
Code (`~/.claude/projects/<encoded-cwd>/*.jsonl`), Codex CLI
(`~/.codex/sessions/**/rollout-*.jsonl`), and Copilot CLI
(`~/.copilot/session-state/*/events.jsonl`); for anything else, use `--source`
or set the `BATON_SOURCE` env var.

### 2. Fill in STATE.md

Write it for an agent with zero memory of this session. Be concrete:

- **Objective** - what the work is for, in a sentence or two.
- **Decisions locked** - the forks already settled and why; the next agent must
  not relitigate them.
- **Done** - finished and verified, with commit/branch/file references.
- **Outstanding** - what is left, in priority order, each item actionable
  without further questions.
- **Landmines / gotchas** - non-obvious traps; failures already hit so they are
  not repeated.
- **Environment** - branch/worktree, how to run and test, required env vars or
  services, anything already running that must not be killed.

### 3. Fill in CONTINUE.md

Pick exactly one target and delete the rest:

- **VERIFY** - a different, ideally more capable, model double-checks the work.
  Pairs well with the rule that the model which produced a plan should not be the
  one that approves it.
- **IMPLEMENT** - a cheaper, faster model builds the approved outstanding items.
- **RESUME** - the same task continues in a new session or on another machine.

Set the repo and branch/worktree, add any task-specific constraints, and keep
the final "restate the plan back to me first" step so the receiving agent
confirms it has the right picture before touching anything.

### 4. Tell the user

Report the folder path, which target you set in CONTINUE.md, and whether a
transcript was captured. Remind them the folder is gitignored. If they asked for
something to paste elsewhere, hand them the contents of CONTINUE.md directly.

## Notes

- Standard library only. No install step.
- `STATE.md` and `CONTINUE.md` are deliberately yours to write; the script will
  not invent decisions it cannot know.
- Transcripts can be large; they are written regardless of size and kept local.
- Pairs naturally with plan-review-hub: that gates what gets approved, baton
  carries approved work across the seams between sessions, models, and machines.
