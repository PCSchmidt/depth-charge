# Depth Charge - Requirements, User Stories and Session Walkthrough

**Status:** Draft v1 - design only
**Companion to:** [SPEC.md](./SPEC.md). Priorities: **P0** first playable (headless + greybox); **P1** first complete game; **P2** later.
**Safety:** This is an entertainment simulation, not training or medical guidance (see SPEC §1, §10).

## 1. User stories and acceptance scenarios

### US-1 (P0) - Complete a constant-weight dive
As a diver, I descend to a target depth, retrieve a tag and return on one breath.
1. **Given** a seeded dive site, **when** I start, **then** I see surface conditions, the line, and optional dive-computer readings; I choose weighting and an announced depth.
2. **Given** I descend, **when** I pass my neutral-buoyancy depth, **then** I accelerate in free fall and my buoyancy feedback changes accordingly.
3. **Given** I do not equalize in time, **then** descent is limited and pain feedback appears; repeated failure ends the dive with a safe recovery.
4. **Given** I reach the tag and ascend, **when** I surface, **then** I must complete the surface protocol within the time window; otherwise the dive is voided.
5. **Given** hypoxia thresholds are exceeded, **then** the dive ends in blackout and is scored accordingly with a clear explanation.

### US-2 (P0) - Physiology is legible
1. **Given** rising CO₂ drive, **then** diaphragm contractions begin at a plausible fraction of the dive and are felt through camera and audio cues.
2. **Given** I relax and streamline, **then** oxygen consumption falls measurably versus tense, inefficient movement.

### US-3 (P0) - Replay and verify
Replays re-simulate to identical depth profiles and outcomes; tampered logs are rejected.

### US-4 (P1) - Other disciplines
FIM, CNF, DYN and STA with their own controls and scoring.

### US-5 (P1) - Use currents and visibility
Route choice in a reef race exploits current; poor visibility changes navigation; in cave swim-throughs silt is a navigational hazard.

### US-6 (P1) - Dive school (tutorial)
Staged lessons with pass criteria: surface breathing and relaxation, duck dive, equalization rhythm, free-fall, turn, ascent, surface protocol.

### US-7 (P1) - Review and coaching
Post-dive depth, heart-rate and O₂ curves with an event timeline; optional coach explains inefficiencies grounded in the log.

### US-8 (P1) - Daily Dive and leaderboard
Seeded dive, verified scores.

### US-9 (P1) - Accessibility
Adjustable rhythm tolerances, alternative inputs, reduced camera shake and tunnel effects, color-blind-safe markers.

### US-10 (P2) - Team mode (3v3 capture the buoy) and co-op safety diver

## 2. Functional requirements

### Physics and physiology
- **FR-001 (P0)** Deterministic: same build + scenario + inputs ⇒ identical profiles and outcomes.
- **FR-002 (P0)** Pressure and lung volume follow Boyle's law; ambient pressure from density and depth.
- **FR-003 (P0)** Net buoyancy accounts for lung volume, suit compression and weighting; neutral buoyancy depth computed analytically in tests.
- **FR-004 (P0)** Drag with orientation-dependent area; stroke model with efficiency optimum; no exploit by input spamming.
- **FR-005 (P0)** Physiology model: O₂ store, CO₂ drive, diving response, mental state, fatigue, cold; archetype parameters.
- **FR-006 (P0)** Equalization mechanic with depth-scaled difficulty and consequences.
- **FR-007 (P1)** Flow fields (tidal, wall, surge, cave) sampled deterministically.
- **FR-008 (P1)** Visibility model: wavelength attenuation, turbidity, silt field.
- **FR-009 (P1)** Narcosis perturbation at depth (subtle, documented).

### Rules and competition
- **FR-020 (P0)** Discipline rules: announced depth, tag retrieval, surface protocol, blackout/penalty handling.
- **FR-021 (P0)** Score is a pure function of the replay.
- **FR-022 (P1)** Server re-simulation verifies leaderboard submissions.

### Presentation
- **FR-030 (P1)** Underwater volume rendering: attenuation, scattering, caustics, light shafts, particulates.
- **FR-031 (P1)** Surface/underwater transition with Snell's window and audio filtering.
- **FR-032 (P1)** Diegetic feedback for physiology; optional dive computer.

### AI (see [ML.md](./ML.md), [AGENTS.md](./AGENTS.md))
- **FR-040 (P0)** Scripted archetype divers for ghost/ladder play.
- **FR-041 (P1)** Learned pacing policy trained in the headless sim; never exceeds physiology limits.
- **FR-042 (P1)** Optional coach is replay-grounded.

### Safety
- **FR-050 (P0)** First-run safety notice and settings access to it at any time.
- **FR-051 (P0)** Blackout is presented as a failure state, not a goal; no content encourages unsafe real-world practice.

## 3. Non-functional requirements
- **NFR-001** ≥ 60 FPS at 1080p on the Reference tier in the worst reef scene (target; S4).
- **NFR-002** Headless sim ≥ 1,000× real time for a single diver on the Dev machine.
- **NFR-003** A dive lasts 2-8 minutes.
- **NFR-004** Single-player offline.
- **NFR-005** Physiology and optical parameters cite sources or are labelled as tunable design values; no medical accuracy claims.

## 4. Session walkthrough (Constant Weight, ~6 minutes)

| Time | Experience | Systems |
|---|---|---|
| 0:00 | Briefing: "Blue-water line, 22 °C, light current, visibility 25 m. Announce depth: 30 m." Choose weighting (neutral at 11 m). | Scenario, FR-003 |
| 0:30 | Surface breathing: relax meter guides a calm breathing cycle; heart rate settles. | FR-005 |
| 1:00 | Duck dive and kick; light shafts and caustics fade; colors shift blue. | FR-008, FR-030 |
| 1:20 | First equalizations come easily; rhythm tightens with depth. A late equalization costs seconds. | FR-006 |
| 1:40 | Pass 11 m: the diver begins to fall. Player stops kicking, streamlines, and relaxes. | FR-003, FR-004 |
| 2:10 | Reach 30 m, grab the tag; first diaphragm contractions begin. | FR-005 |
| 2:20 | Turn and ascend with measured kicks; tunnel vision begins around 12 m. | FR-005, FR-032 |
| 3:00 | Surface; remove mask, signal, speak within time window. Protocol passed. | FR-020 |
| 3:30 | Debrief: depth/heart/O₂ curves, stroke efficiency, equalization timing. Optional coach comments. | US-7 |

## 5. Traceability
FRs map to spikes S1-S12 in [SPIKES.md](./SPIKES.md) and automated tests; `docs/TRACEABILITY.md` created at implementation start.
