# Source recordings

The original takes, before splitting. `ear/raw/` holds the per-word clips cut
out of these; `ear/audio/` holds the trimmed and levelled mp3s built from
those. Both of those are regenerable — **these files are not.**

They live here rather than on somebody's desktop because the settings below
are only useful next to the audio they describe, and because a pipeline whose
sources sit outside the repo is a trap the first time a take needs re-cutting
— a different `--reps`, a corrected reading order, a better silence floor.

| file | speaker | read | reps | split with |
|---|---|---|---|---|
| `frank0.wav` | frank | all 23 s/sz/ś words | 1 | defaults, in the original SETS order |
| `frank1.wav` | frank | the 16 c/cz/ć words | 1 | `--subset nic,nic-acute,…` |
| `frank2.wav` | frank | all 39 | 3 | `--reps 3 --noise=-40dB` |
| `alan0.mov` | alan | the first 10 of the reading order | 2 | `--reps 2 --speaker alan` |
| `alan1.mov` | alan | all 39 | 2 | `--reps 2 --noise=-30dB --speaker alan` |

The `--subset` argument always comes from `ear/reading-order.txt`, which is
the one fixed order every reader is given. `frank0` and `frank1` predate it
and were read in SETS order instead, which is why their entries above name a
different order — if either is ever re-cut, use the order it was actually
read in, not the current sheet.

## Why the noise floors differ

`--noise` sets what counts as silence between words, and the right value is a
property of the room, not of the words. Too sensitive and a breath becomes a
word; too blunt and two words merge. The splitter refuses to write unless the
segment count comes out exactly right, so the value below is simply the one
that made the count match:

- `frank2.wav` needed **-40dB**: at the -35dB default one take was too quiet
  to detect and the count came up one short.
- `alan1.mov` needed **-30dB**: at -35dB it found 79 segments and at -40dB 82,
  both counting breaths as words. -30dB gives 78 stably at every gap setting.

Raising the floor risks clipping a quiet frication onset, which is exactly
what the trainer is about — but `ear_split.py` keeps 0.20s of padding around
every cut, and `ear_build.py` trims with a 0.15s pad at -50dB, so the onset
survives a late detection.
