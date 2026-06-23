#!/usr/bin/env python3
"""
baton - hand off agent work between sessions, models, and machines.

Zero dependencies (Python standard library only). Provider-agnostic.

baton does the plumbing for a clean handoff:
  - finds the current agent's session state (Claude Code, Codex, Copilot, or a
    file you point it at),
  - reconstructs a readable transcript,
  - scaffolds a portable handoff package (STATE.md + CONTINUE.md) in handoff/,
  - keeps handoff/ out of git.

It deliberately does NOT write the contents of STATE.md / CONTINUE.md for you.
Those hold judgement (what was decided, what is left, what the next agent must
know) and should be filled in by the agent that did the work. baton gives you
the folder, the templates, and the transcript; you supply the thinking.

Usage:
  python3 baton.py new "short-slug" [--source PATH] [--no-transcript]
  python3 baton.py detect          # print where session state was found
  python3 baton.py list            # list existing handoffs

Auto-detection covers Claude Code (~/.claude/projects/<encoded-cwd>/*.jsonl),
Codex CLI (~/.codex/sessions/**/rollout-*.jsonl), and Copilot CLI
(~/.copilot/session-state/*/events.jsonl). For anything else, point it at the
log with --source or the BATON_SOURCE env var.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HANDOFF_DIR = Path("handoff")


# --------------------------------------------------------------------------- #
# Session-state detection (provider-agnostic, best-effort)
# --------------------------------------------------------------------------- #
def _claude_code_state(cwd: Path):
    """Claude Code stores transcripts at ~/.claude/projects/<encoded-cwd>/*.jsonl
    where the cwd has every '/' replaced by '-'."""
    encoded = str(cwd).replace("/", "-")
    proj = Path.home() / ".claude" / "projects" / encoded
    if proj.is_dir():
        files = sorted(proj.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
        if files:
            return files[-1]
    return None


def _copilot_state():
    """GitHub Copilot CLI stores events at ~/.copilot/session-state/<id>/events.jsonl."""
    root = Path.home() / ".copilot" / "session-state"
    if root.is_dir():
        candidates = sorted(root.glob("*/events.jsonl"), key=lambda p: p.stat().st_mtime)
        if candidates:
            return candidates[-1]
    return None


def _codex_state():
    """OpenAI Codex CLI stores rollouts at ~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl."""
    root = Path.home() / ".codex" / "sessions"
    if root.is_dir():
        files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime)
        if files:
            return files[-1]
    return None


def detect_source() -> Optional[Path]:
    """Return the most likely session-state file, or None.

    Order: explicit env override, then the most recently touched of Claude Code
    (for this cwd), Codex, and Copilot.
    """
    env = os.environ.get("BATON_SOURCE")
    if env and Path(env).is_file():
        return Path(env)
    cwd = Path.cwd()
    found = [f for f in (_claude_code_state(cwd), _codex_state(), _copilot_state()) if f]
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


# --------------------------------------------------------------------------- #
# Transcript reconstruction
# --------------------------------------------------------------------------- #
_TEXT_BLOCK_TYPES = {"text", "input_text", "output_text"}


def _text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in _TEXT_BLOCK_TYPES:
                parts.append(block.get("text", ""))
        return "\n".join(p for p in parts if p)
    return ""


def _is_noise(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return True
    markers = (
        "<local-command", "<command-name", "<command-message", "caveat:",
        "<system-reminder", "tool_result", "<bash-", "do not respond",
        "[request interrupted",
    )
    return any(m in t for m in markers)


def reconstruct_transcript(source: Path) -> str:
    """Pull user/assistant text turns out of a .jsonl session file."""
    turns = []
    for line in source.read_text(errors="ignore").splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("isMeta"):
            continue
        typ = o.get("type")
        # Claude Code: o.message; Copilot: o.data; Codex: o.payload (a nested
        # response item). Take whichever carries the role + content.
        msg = o.get("message") or o.get("data") or o.get("payload") or {}
        if not isinstance(msg, dict):
            continue
        role = msg.get("role") or (typ if typ in ("user", "assistant") else None)
        if role not in ("user", "assistant"):
            continue
        text = _text_from_content(msg.get("content"))
        if not text or _is_noise(text):
            continue
        turns.append((role, text.strip()))

    out = [f"# Transcript (reconstructed)\n", f"Source: `{source}`\n"]
    for role, text in turns:
        who = "User" if role == "user" else "Assistant"
        out.append(f"\n**{who}:** {text}\n")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Templates (the agent fills these in)
# --------------------------------------------------------------------------- #
STATE_TEMPLATE = """# Handoff state: {slug}

> Written for a fresh agent with no memory of this session. Be specific. Assume
> nothing carried over except this file and the repo.

## Objective
<!-- One or two sentences: what is this work trying to achieve? -->

## Decisions locked (do not relitigate)
<!-- The forks already settled, and why. The next agent must respect these. -->
-

## Done
<!-- What is finished and verified. Reference commits/branches/files. -->
-

## Outstanding (in priority order)
<!-- What is left. Each item concrete enough to act on without asking. -->
1.

## Landmines / gotchas
<!-- Non-obvious things that will bite the next agent. Failures already hit. -->
-

## Environment
- Branch / worktree:
- How to run / test:
- Required env vars or services:
- Anything already running that must not be killed:
"""

CONTINUE_TEMPLATE = """# Continuation prompt: {slug}

> Paste the block below into a fresh agent session. Pick ONE target and delete
> the others. Keep STATE.md alongside it so the agent can read full context.

## Target: pick one
- [ ] VERIFY  - a different, more capable model double-checks the plan/work
- [ ] IMPLEMENT - a cheaper, faster model builds the approved outstanding items
- [ ] RESUME  - same task, new session/machine, continue where this left off

---

You are picking up work in progress. Read `STATE.md` in this folder in full
before doing anything; it is the source of truth for what was decided and what
is left.

Repository: <repo + branch/worktree>
Your role: <VERIFY | IMPLEMENT | RESUME - keep one, match the box above>

Rules:
- Respect every item under "Decisions locked". Do not redesign settled choices.
- Work only on the "Outstanding" items, top of the list first.
- If something in STATE.md is ambiguous, ask before acting - do not guess.
- <add task-specific constraints here>

First action: restate the objective and the outstanding list back to me in your
own words so I can confirm you have the right picture before you start.
"""


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _next_number() -> str:
    HANDOFF_DIR.mkdir(exist_ok=True)
    nums = []
    for child in HANDOFF_DIR.iterdir():
        m = re.match(r"(\d{3})-", child.name)
        if m:
            nums.append(int(m.group(1)))
    return f"{(max(nums) + 1) if nums else 1:03d}"


def _ensure_gitignored():
    gi = Path(".gitignore")
    existing = gi.read_text() if gi.is_file() else ""
    if "handoff/" not in existing:
        with gi.open("a") as fh:
            fh.write("\n# baton handoffs (local only)\nhandoff/\n")


def cmd_new(slug: str, source_override: Optional[str], want_transcript: bool):
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "handoff"
    number = _next_number()
    folder = HANDOFF_DIR / f"{number}-{slug}"
    folder.mkdir(parents=True)

    (folder / "STATE.md").write_text(STATE_TEMPLATE.format(slug=slug))
    (folder / "CONTINUE.md").write_text(CONTINUE_TEMPLATE.format(slug=slug))

    transcript_note = "skipped"
    if want_transcript:
        source = Path(source_override) if source_override else detect_source()
        if source and source.is_file():
            try:
                (folder / "transcript.md").write_text(reconstruct_transcript(source))
                transcript_note = f"from {source}"
            except Exception as exc:  # noqa: BLE001
                transcript_note = f"failed ({exc})"
        else:
            transcript_note = "no session state found (fill STATE.md by hand)"

    _ensure_gitignored()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"baton: created {folder}/  ({stamp})")
    print(f"  STATE.md      - fill in: decisions, done, outstanding, gotchas")
    print(f"  CONTINUE.md   - pick a target, set repo/branch")
    print(f"  transcript.md - {transcript_note}")
    print("  handoff/ is gitignored")


def cmd_detect():
    source = detect_source()
    print(source if source else "baton: no session state detected "
          "(set BATON_SOURCE=/path/to/session.jsonl)")


def cmd_list():
    if not HANDOFF_DIR.is_dir():
        print("baton: no handoffs yet")
        return
    for child in sorted(HANDOFF_DIR.iterdir()):
        if child.is_dir():
            print(child.name)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "new":
        if not rest:
            print("usage: baton.py new \"short-slug\" [--source PATH] [--no-transcript]")
            return 2
        slug = rest[0]
        source = None
        if "--source" in rest:
            source = rest[rest.index("--source") + 1]
        cmd_new(slug, source, want_transcript="--no-transcript" not in rest)
    elif cmd == "detect":
        cmd_detect()
    elif cmd == "list":
        cmd_list()
    else:
        print(f"baton: unknown command '{cmd}'")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
