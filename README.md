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
