# Memory Bank (Antigravity-style)

Use when starting a session, resuming work after a break, completing significant work,
or when the user asks to save/update memory. Mimics the Antigravity community memory-bank
pattern: file-based context + daily session logs, complementing opencode-mem vectors.

## Session Start Ritual

1. Read `~/.config/opencode/memory/context.md` first.
2. If today's session log `~/.config/opencode/sessions/YYYY-MM-DD.md` is missing, create it.
3. Show a one-line status: `🧠 Memory: <one-line summary from context.md>`
4. If context.md is empty/stale or the user asks, offer to initialize memory for the
   current project before starting work.

## Update Ritual (after significant work / "remember this")

1. Update `memory/context.md` — current state only: active project, in-flight work,
   next steps. Keep under 3KB. Delete stale entries.
2. Append to `sessions/YYYY-MM-DD.md` (create if missing):
   `- HH:MM : <what happened>` — factual, short.
3. Move durable knowledge (tools, commands, gotchas, user prefs) to
   `tech-stack.md` / `patterns.md` / `USER.md` instead of context.md.
4. Do not log trivial turns; log decisions, completions, discoveries, blockers.

## RECAP Ritual (long sessions / before compaction or ending)

1. Append a `## RECAP` section to today's session log with timestamped entries of
   everything significant this session.
2. Ensure context.md reflects the final state so the next session picks up cleanly.
3. Say `🧠 RECAP saved.` when done.

## Rules

- Keep entries SHORT and FACTUAL. No prose, no fluff.
- Never override USER.md — only suggest changes.
- Sessions log = history; context.md = RAM; tech-stack/patterns = durable knowledge.
- If opencode-mem is available, also store important facts via its add-memory tool.
