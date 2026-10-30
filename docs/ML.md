# Depth Charge - Machine Learning Specification

**Status:** Draft v1 - design only
**Standard:** Problem formulation, data, baseline, metrics, ablations, reproducible training, export, model card, CI evaluation. Thresholds are targets to justify.

## 0. Common infrastructure
Headless deterministic simulation with Python bindings and Gymnasium-style environments; seeded scenarios; split by seed and site; PyTorch; config-driven training; experiment tracking; ONNX export with parity test; bootstrap CIs; model cards.

## 1. Pacing and technique policy (flagship)
- **Problem:** choose descent speed, kick cadence, relaxation level, turn depth and ascent profile to maximize score for a given physiology archetype without exceeding safety limits.
- **Formulation:** constrained optimal control / POMDP. Observations: depth, vertical speed, lung-volume estimate, stroke state, equalization state, heart rate, urge-to-breathe proxy (what the player can feel; not true O₂). Actions: high-level (kick amplitude and cadence, glide, relax toggle, turn command) at ~2 Hz.
- **Training:** PPO with constraint handling (Lagrangian or safety layer) so blackout and barotrauma are penalized and exceeded limits are infeasible.
- **Baselines:** analytic optimal-control solution for a simplified model (dynamic programming); heuristic pacing bot; random.
- **Metrics:** score vs analytic optimum (gap %); blackout/barotrauma rate (must be ≈0 for the shipped bot); robustness to parameter perturbation (cold, current, different archetype).
- **Ablations:** observation set (with/without urge proxy), reward shaping, constraint method.
- **Value:** a safe-RL case study with a ground-truth optimum to compare against.

## 2. Physiology parameter identification
- **Problem:** choose model parameters so that archetype dive durations and responses fall within plausible published ranges.
- **Approach:** approximate Bayesian computation or Bayesian optimization against target distributions (static times, dive times by depth), with documented priors and sources.
- **Metrics:** match to target ranges, parameter posterior widths, sensitivity analysis (Sobol indices or one-at-a-time).
- **Honesty requirement:** this tunes a game model for plausibility; no medical claims.

## 3. Stroke technique analysis (supervised)
- **Problem:** classify inefficient technique (e.g., over-kicking in free fall, late relaxation) from dive logs to drive coaching feedback.
- **Data:** labelled synthetic dives from perturbed policies with known inefficiencies; held-out human logs from the owner as qualitative check.
- **Models:** GBM on engineered features vs a small 1-D CNN on time series.
- **Metrics:** per-class precision/recall; calibration; explanation faithfulness (feature attributions vs known injected faults).

## 4. Visibility and optics model validation
Not ML, but data-driven: fit attenuation coefficients to published water-type data by least squares with uncertainty; verify the rendered colors against the model (S3).

## 5. Rating and integrity
Skill rating per discipline (Glicko-2/TrueSkill comparison on bot tournaments); anomaly detection on input logs (impossible stroke rates, equalization timing) with synthetic cheater policies; recall at fixed FPR.

## 6. Release checklist and evaluation matrix
Per model: config/seed/commit/data hash; one-command reproduction; held-out evaluation with CI; ONNX parity; model card; negative results retained.

| Component | Primary metric | Baseline | Split |
|---|---|---|---|
| Pacing policy | Score gap to analytic optimum; blackout rate | DP optimum, heuristic | Held-out sites/archetypes |
| Parameter ID | Range match, sensitivity | Hand-tuned | n/a |
| Technique classifier | Precision/recall | Rule thresholds | Held-out synthetic dives |
| Ratings | Predictive log-likelihood | Elo | Bot tournaments |
| Anomaly detector | Recall @ fixed FPR | Rule thresholds | Held-out replays |
