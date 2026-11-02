# C0 evidence: headless dive model (spikes S1, S2, S7, S8)

**Date:** 2026-11-02. **Code:** `python/depthcharge/` (pure Python, standard library only). **Tests:** `python/tests/` (32 pass). **Status:** the model exists and the four spikes pass *as written*; read the caveats before treating "pass" as more than that.
This is a gameplay model. It is not medical or training guidance, and no parameter is a measurement of a human.

## What was built
- `model.py`: ambient pressure, Boyle lung volume, compressing wetsuit, net buoyancy with a closed-form neutral depth, quadratic drag, kick thrust with a log-normal frequency optimum.
- `dive.py`: one diver on a line. O2 store and CO2 tension, diving response with ramp, stress, fatigue, ear-pressure gauge with an equalization action (seeded RNG, the only randomness), Constant Weight rules (announced depth, tag, turn, surface protocol with deadlines) and a Static hold. Replay is the controls log; `verify` accepts a dive only if re-simulation reproduces its digest.
- `bots.py`: scripted archetype divers (novice, trained, elite). They see only what a diver could feel or read, never true O2 or CO2.

## S1: pressure, lung volume, buoyancy: PASS
- Lung volume x pressure equals surface volume x surface pressure within 0.1% at 0, 3, 10, 25, 40 m. A 6 L breath is 3.01 L at 10 m (0.502 of the surface volume in sea water; the spec's "halves by 10 m" is the fresh-air approximation) and 1.21 L at 40 m.
- Neutral depth: the closed form equals the numerical root of the net-buoyancy force within 1 cm for 10 weightings (0 to 4.5 kg). More lead gives a shallower neutral depth (16.3 m at 0 kg, 10.3 m at 1.2 kg, 3.3 m at 4 kg); 8 kg sinks at the surface (no neutral point).
- Direction: 3 m deeper than neutral the diver accelerates down; 3 m shallower, up.

## S2: archetype plausibility: PASS against the stated ranges (circular, see caveats)
| Archetype | Static break | Contractions begin | 30 m dive | 40 m dive |
|---|---|---|---|---|
| novice (range 1-2.5 min) | 2.19 min | 59% of the time | 107 s, safe | black-out (beyond its limits, as intended) |
| trained (3-6 min) | 4.60 min | 60% | 99 s | 126 s, safe |
| elite (7+ min) | 8.53 min | 63% | 96 s | 122 s, safe |
Depth dives were played by the scripted diver at about 0.75 m/s with 16-23 equalizations. Blackout happened only where the model's limit is exceeded; a comfortable dive never reaches the samba zone.

## S7: stroke model: PASS
Kick effectiveness peaks at 0.8 Hz. Speed per unit oxygen at a fixed amplitude has an interior optimum (about 0.7 Hz). Kicking at 1.6 Hz is slower than at 0.8 Hz and costs four times the work term, so button-mashing does not pay.

## S8: determinism: PASS
5,000 dives (random archetype, depth, weighting, bot speeds, time step 20 or 50 ms, seed), each simulated directly, replayed from its controls log, and again in a separate worker process: 0 replay mismatches, 0 cross-process mismatches (`tools/s8.py`, `S8.json`; Python 3.14.6, one machine). 4,839 successes and 161 blackouts (random depth against archetype). Tampered logs (an equalization removed, stronger kicks, an unknown control) are rejected.

## Speed (NFR-002, 1,000x real time)
7,600x at a 50 ms step; 1,600x at a 10 ms step, one process. The spec's 5-10 ms step is therefore affordable; the default stays 50 ms for the prototype.

## Caveats
1. **S2 is a calibration, not a validation.** I tuned the design values until the archetypes landed in the ranges written in SPIKES.md, and those ranges carry no cited source (`[VERIFY]`). Passing says the model can reproduce numbers I chose, not that it is right.
2. **Hyperventilation, lung squeeze and mouthfill are deliberately not modelled.** Depth is capped at 40 m (lung gas reaches about 1.2 L). Hyperventilation is left out on purpose: it is the classic way to delay the urge to breathe while hypoxia keeps building, and putting it in as a game lever would read as instruction (SPEC safety pillar).
3. **Bots play perfectly timed equalization.** Human difficulty is unmeasured; the equalization gauge (ear excess against pain 12%, lock 20%, injury 35%) is a first guess.
4. **Determinism is one language runtime on one machine.** Cross-platform floating point (the spec's 'two builds') has not been tested.
5. **One-dimensional.** The diver moves along a vertical line; there is no horizontal motion, current or visibility yet (C5/C6).
