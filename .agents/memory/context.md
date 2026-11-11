# Active Context: AniDoc AI Automation (@Jazzcreatesclips)

Active Project: `anidoc-ai-automation` at `~/anidoc-ai-automation`
Channel: `@Jazzcreatesclips` on YouTube Shorts (https://www.youtube.com/channel/UCW-tzdlwTcHHCwNWlyLQ1hQ)
Core Function: Automated 4K HDR Phonk Scene Edit Engine for Demon Slayer & Jujutsu Kaisen.

## Active Production State
- Branch: `main`
- Target Duration: 18.0s (high-retention viral sweet spot)
- Letterbox Framing: Interactive discussion hooks (prompting comments)
- Duplicate Prevention: Persistent title history tracked in `.agents/data/title_history.json`
- Schedule: Twice-daily automated publishing via `.github/workflows/daily_edit.yml`
  - 06:30 UTC Morning Slot: Demon Slayer (Kimetsu no Yaiba)
  - 18:30 UTC Evening Slot: Jujutsu Kaisen (JJK)
- Workflow Status: Run 37171219344 passed cleanly with Inosuke 4K Edit published to YouTube Shorts (https://youtube.com/shorts/gGINUTqY9tw).
- 2026-11-10 incident: run fired ~8.5h late (free-runner cron drift); CandleGate blocked at 22.5h elapsed and discarded the render (commit 2e56836 wiped test-mock history entries).
- Fix A (2026-11-11, applied locally, NOT pushed): `publishers/candle_gate.py` inline spacing window 0.5h → 4.0h (covers runner drift up to 4h); `publishers/youtube_publisher.py` re-evaluates the gate after the inline sleep (defers if Layer 1/2 flips). Awaiting push approval.
- Test Suite: test_candle_gate 9/9 OK, test_youtube_publisher 10/10 OK (both suites re-validated after Fix A).

## Universe Quarantine Architecture
- Filename Matching: `core/timestamp_loader.py` uses separate Demon Slayer (`DS_SxxExx`) and JJK (`SxxExx`) regex branches with zero fallthrough.
- Google Drive Ingestion: `core/gdrive_manager.py` verifies `get_file_universe()` before selection; rejects non-matching franchise files.
- Slicer Protection: `slice_action_moments_from_source()` asserts matching universe before generating cuts.
- Metadata & SEO: `core/quote_ai.py` enforces keyword boundary sets (`DEMONSLAYER_KEYWORDS` vs `JJK_KEYWORDS`), sanitizes tags, and generates canonical series descriptions.

## Character Rosters
- Demon Slayer: Tanjiro, Rengoku, Zenitsu, Akaza, Giyu, Tengen, Inosuke, Muzan, Nezuko, Muichiro, Gyutaro.
- Jujutsu Kaisen: Gojo, Sukuna, Toji, Yuji, Megumi, Nobara, Todo, Mahito, Choso.

## Hardware & Deployment Constraints
- Local Device: Physical Android Phone with Termux (~1.2GB RAM free). Strictly surgical edits, configs, and unit testing locally.
- Heavy Compute: All FFmpeg 4K video rendering and YouTube uploads execute on GitHub Actions (`ubuntu-latest` runner).
