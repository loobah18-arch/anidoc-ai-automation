# Active Context: AniDoc AI Automation (@jazzcreates)

Active Project: `anidoc-ai-automation` at `~/anidoc-ai-automation`
Channel: `@jazzcreates` on YouTube Shorts
Core Function: Automated 4K HDR Phonk Scene Edit Engine for Demon Slayer & Jujutsu Kaisen.

## Active Production State
- Branch: `main` (commit `ff23584` / latest)
- Schedule: Twice-daily automated publishing via `.github/workflows/daily_edit.yml`
  - 06:30 UTC Morning Slot: Demon Slayer (Kimetsu no Yaiba)
  - 18:30 UTC Evening Slot: Jujutsu Kaisen (JJK)
- Workflow Status: Run 37171219344 passed cleanly with Inosuke 4K Edit published to YouTube Shorts (https://youtube.com/shorts/gGINUTqY9tw).
- Test Suite: 15/15 tests passing (`test_detailed_episodes.py` 8/8, `test_pipeline.py` 7/7).

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
