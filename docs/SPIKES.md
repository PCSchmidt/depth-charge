# Depth Charge - Verification Spike Ladder

**Created:** 2026-10-29 | **Status:** Not started

| ID | Question | Build | Pass criteria | If it fails |
|---|---|---|---|---|
| **S1** | Are pressure, lung volume and buoyancy correct? | Headless depth/buoyancy model; weighting presets | Lung volume ratio matches Boyle within 0.1%; neutral buoyancy depth equals analytic value for 10 weighting cases; free-fall acceleration direction correct | Fix unit/density handling |
| **S2** | Do physiology archetypes give plausible dives? | Coupled O₂/CO₂/diving-response model; archetypes (novice, trained, elite) | Static: novice 1-2.5 min, trained 3-6 min, elite 7+ min; 30-50 m dive: 1.5-3 min at moderate effort; contractions begin at 50-70% of max time; blackout only when limits are exceeded | Recalibrate rates; adjust diving-response gains |
| **S3** | Does the visibility model produce correct color loss? | Wavelength attenuation with water-type presets | Captured-frame measurements: red channel drops to ≤ 10% at 10 m in clear water; ratio matches coefficients within 10% | Fix color pipeline/tonemapping |
| **S4** | Can underwater rendering meet budget? | Reef scene: caustics, volumetric shafts, marine snow, 100 fish | Reference tier ≥ 60 FPS 1080p; Dev laptop ≥ 40 FPS fallback tier; 1% lows reported | Lower volumetric resolution; fewer particles; simpler caustics |
| **S5** | Does the surface/underwater transition work? | Camera crossing the HROcean surface | No visible seam or popping; Snell's window geometry within 2° of analytic; correct audio filter switch | Fix camera volume and refraction |
| **S6** | Is the equalization mechanic fair and fun? | Timed equalize input with depth-scaled windows | Owner can complete a 30 m dive with ≥ 80% success at standard assist after 5 attempts; failure leads to clear feedback; log confusion | Widen windows; revise input |
| **S7** | Is the stroke model sensible? | Stroke efficiency vs frequency/amplitude | Speed vs frequency curve has a clear optimum; very high frequency is inefficient; no exploit by button-mashing | Add efficiency penalty/fatigue |
| **S8** | Is the sim deterministic? | 5,000 dive replays x 2 builds/threads | Zero hash mismatches | Fix RNG/float path |
| **S9** | Do currents matter without overwhelming? | HRFlow reef scene | Optimal route saves ≥ 10% O₂ vs straight line; no route requires impossible effort | Retune strength |
| **S10** | Is surface protocol readable and fair? | Interactive surface step with timing | ≥ 90% of valid dives pass with correct input; failure states explained | Revise UX |
| **S11** | Can bots learn pacing without cheating? | RL on headless sim with same inputs | Bot approaches near-optimal descent profile (within 5% of analytic optimum) and never exceeds physiology limits | Fix reward shaping; constrain actions |
| **S12** | Does the cave silt mechanic work? | Silt field + particle visuals | Silt visibility effects deterministic; owner can navigate a short swim-through; kicks create expected reduction | Tune decay/visibility |

## Order
S1 → S2 → S3 → S4/S5 → S6/S7 → S8 → S9/S10 → S11 → S12.

## Evidence format
`docs/spike-results/Sx.md` with commit, build, inputs, plots, verdict, date. Retain failed attempts.
