# C3 evidence: Free Immersion, Constant No-Fins, Dynamic (and Static)

**Date:** 2026-11-04. **Code:** `python/depthcharge/` (dive.py, model.py, bots.py, play/). **Tests:** `python/tests/test_c3.py` (16 more; 53 total). Gameplay model, not training or medical guidance; every number is a design value.

## What was added
- **FIM** and **CNF**: the same vertical dive as CWT with a different stroke (`model.STROKES`: optimal rate, width, thrust scale). FIM pulls at about 0.35 Hz with 0.75x the fin thrust, CNF 0.3 Hz with 0.6x. Default weighting is heavier (FIM 2.5 kg, CNF 3.0 kg) because arms cannot beat the surface buoyancy that a fin kick can.
- **DYN**: horizontal swim in a pool at a fixed trim just under the surface (no ears, no depth). Announced distance (25-300 m), pool length, turns allowed only at a wall (1.5 s, then a push-off), `finish` ends the swim and starts the same surface protocol. Score is the distance, minus 10 for a hypoxic samba.
- **STA** was already in C0 (headless only; no client view yet).
- Scripted divers (`ScriptedDiver` parameters, new `DynDiver`) and ghosts for all of them; client discipline selector, pool view for DYN, per-discipline coach text.
- CWT and STA are unchanged: digests of 28 fixed dives are identical to the previous commit.

## Calibration (scripted divers, seed 3; not a validation)
| | novice | trained | elite |
|---|---|---|---|
| FIM, deepest bot success tested | 20 m | 40 m | 40 m |
| CNF | 10 m | 20 m (30 m blackout) | 40 m |
| DYN | 100 m | 200 m (with samba) | 250 m |
Ordering is what the design asks for (fins > pull > no-fins; novice < trained < elite). The absolute numbers are tuned values with no cited source ([VERIFY]); the same circularity caveat as S2 applies.

## Known limits
- Replay determinism for the new disciplines is tested on 36 random dives (not 5,000), one machine.
- CNF novices barotrauma at 20 m+ in the bot runs because the heavy weighting makes them fall faster than the scripted equalization keeps up; real players may do better or worse (unmeasured).
- DYN has no strokes rhythm, glide or wall-turn skill yet; the client's DYN view was checked by screenshot in headless Edge only.
- No human has played FIM, CNF or DYN.
