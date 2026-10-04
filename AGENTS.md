# Agent Guidelines & Memory Protocol (AniDoc AI Automation)

Welcome to `anidoc-ai-automation`. This repository automates 4K HDR Phonk / Scene Edits for the `@jazzcreates` YouTube channel, featuring Demon Slayer and Jujutsu Kaisen.

## 1. Persistent Memory Protocol (DO NOT START FROM SCRATCH)
At the start of ANY session or task:
1. **Read `.agents/memory/context.md` first**: This contains the live production state, character rosters, working configs, and active workflows.
2. **Consult `.agents/memory/patterns.md`**: Review durable lessons learned (anti-leak universe isolation, filename parsing, description formatting, and gotchas).
3. **Use `.agents/data/` for Pre-Seeded Baselines**:
   - `competitor_radar_state.json`: Already has tracked anime edit competitor channels and recent viral formats. Never start from empty state.
   - `creator_baselines.json`: Contains engagement baselines and proven viral reference formulas.
   - `channel_profile.json`: Exact production specifications for `@jazzcreates`.
4. **Update `.agents/memory/context.md`**: Keep it updated after making significant changes or discovering new patterns.

## 2. Hard Constraints & Production Rules
- **ZERO CROSS-UNIVERSE LEAKS**:
  - Demon Slayer edits MUST use Demon Slayer footage, Demon Slayer quotes, and Demon Slayer titles/tags/descriptions.
  - JJK edits MUST use JJK footage, JJK quotes, and JJK titles/tags/descriptions.
  - Never allow filename fallthrough or unvalidated Drive selection across universes.
- **ACCURATE METADATA & DESCRIPTIONS**:
  - Descriptions must explicitly state the canonical series name in English & Japanese (`Demon Slayer: Kimetsu no Yaiba (鬼滅の刃)` vs `Jujutsu Kaisen (呪術廻戦)`), the character name, the quote, and Fair Use copyright disclaimers (ufotable / MAPPA).
- **NO HEAVY LOCAL CODING/RENDERING ON PHONE**:
  - The local device is an Android phone running Termux with ~1.2GB RAM free.
  - NEVER execute full 4K 60-second video encoding, heavy compilations, or memory-intensive suites locally.
  - All heavy rendering, CI/CD, and uploads run via GitHub Actions (`.github/workflows/daily_edit.yml`).
  - Keep local changes surgical, minimal, and Karpathy-compliant.
