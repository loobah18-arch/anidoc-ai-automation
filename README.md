# gojo-amv-exact

Standalone rebuild of the Gojo AMV (DYGO - Funk Infernal): 71 beat-synced cuts at 130 BPM, 1920x1080, 60 seconds.
Footage comes only from the Jujutsu Kaisen episodes in the Google Drive folder (S1E07, S2E04, S2E09).

Every push to this branch (or a manual run from the Actions tab) renders the edit and attaches
`Gojo_AMV_Funk_Infernal.mp4` to the run as a downloadable artifact. Nothing is uploaded to YouTube.

- `edit/shots.json` - every shot's episode and in/out time
- `edit/plan.txt` - which shot lands on which beat
- `edit/pro_fx.py` - punch-ins, whips, flashes, shakes, beat pulses
- `edit/render.py` - renders each shot with its effects
- `edit/build.sh` - downloads episodes, renders, joins, adds the music

## Auto AMV (`auto_amv.yml`)
Each run lists the whole Drive folder (and sub-folders) itself, so a new anime or new episode
dropped into Drive is used without editing anything. Episodes added since the last run are used
first; otherwise it rotates to the least-used anime and its least-used episodes. Output is 1:1 (1080x1080).
Manual run input `pick`: `auto`, an anime name (`demon slayer`), or a character (`gojo` ...).
File names need a season/episode marker (S01_E07, S1E7, Episode 7, "Show - 07"); movies are ignored.
