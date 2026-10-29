# Depth Charge - Architecture and Scoping Specification

**Created:** 2026-10-29
**Status:** Draft v1 - design only; nothing implemented or verified
**Platform dependency:** [hyperreal-platform](https://github.com/PCSchmidt/hyperreal-platform) (HRCore, HRScenario, HRReplay, HRFlow, HROcean, HRGeo, HRNet, HRRating, HRAgents)
**Companion:** [SPIKES.md](./SPIKES.md)

> `[VERIFY]` marks assumptions not yet checked. The physiology model is for gameplay and is **not medical or training guidance**.

---

## 1. Vision

**Pitch.** Competitive breath-hold diving in photoreal water. Players race and compete on a single breath while managing oxygen, buoyancy, equalization, current and visibility - a game of calm efficiency under rising physiological pressure.

**Player fantasy.** Descend through shafts of light into a blue that swallows red, pass the neutral-buoyancy point and fall free, equalize on time, turn at depth, and climb back with burning lungs and perfect technique - alone, against a ghost, or racing a rival through a reef or cave.

**Pillars**
1. **The body is the resource.** O₂, CO₂ tolerance, heart rate, lung volume and mental state are modeled as one system that creates tension without a HUD gimmick.
2. **Efficiency wins.** Streamlining, fin technique, relaxation and route choice beat brute speed.
3. **Water is a character.** Light absorption, particulates, caustics, currents and pressure shape both beauty and play.
4. **Honest visuals.** Visibility, color loss and current streaming come from the sim fields.
5. **Safe and respectful.** The game portrays risk (blackout, squeeze) but does not instruct unsupervised real-world breath-hold diving; safety messaging is prominent.

**Non-goals (v1):** scuba/rebreather diving, deep decompression modeling, spearfishing/hunting, shark-attack horror, multi-hour open-world exploration, full marine ecosystem simulation, medical accuracy claims.

---

## 2. Competitive design

### 2.1 Disciplines and modes

| Mode | Description | Netcode |
|---|---|---|
| **Constant Weight (CWT)** | Dive with fins to a target depth, retrieve a tag, return; announce depth in advance (announced-depth risk/reward) | Async/ghost |
| **Free Immersion (FIM)** | Pull along the line, no fins | Async |
| **Constant No-Fins (CNF)** | Breaststroke technique only | Async |
| **Dynamic (DYN)** | Horizontal distance in a pool; technique and pacing | Async |
| **Static (STA)** | Hold breath motionless; mental-state minigame (relaxation, contraction management) | Async |
| **Reef Race** | Time trial through a marked reef course; routing, current use, ascent/descent management | Async / live |
| **Cave Swim-Through** | Follow a guideline through restrictions with limited visibility and silt; short, controlled distance | Async |
| **Object Recovery** | Retrieve tagged objects from wrecks/seabed within oxygen budget | Async |
| **Capture the Buoy (3v3)** | Team objective underwater; players must surface to breathe; contested zones, currents, and line of sight | Live (phase 2) |
| **Daily Dive** | Seeded course, conditions and depth targets | None (async) |
| **Safety Diver (co-op)** | A partner role: monitor and assist an ascending diver (cooperative) | Live (later) |

### 2.2 Scoring
- Depth/distance/time per discipline with technique penalties (blackout = disqualification; "hypoxic samba" warning mid-ascent costs points; surface protocol: remove mask, OK sign, speak within a time).
- Surface protocol (the "Surface Protocol" at the end of a dive) is an interactive step: failing it voids the dive - a signature mechanic borrowed from competition rules.
- Team modes: objective score and survivability.
- Ratings: per discipline; team ratings for 3v3.

### 2.3 Anti-cheat
Deterministic sim; server re-simulation; input bounds (stroke rate, equalization timing); telemetry anomaly screening.

---

## 3. Simulation architecture

### 3.1 Diver body dynamics
- **Kinematics:** a diver as a rigid-body-with-articulation (head, torso, legs) for hydrodynamic drag orientation; 6-DOF with orientation control via body posture and fin strokes.
- **Hydrodynamics:** quadratic drag with orientation-dependent `Cd·A` (streamlined vs. broadside), added mass, buoyancy force from displaced water, thrust from stroke model.
- **Stroke model (fins):** periodic thrust with efficiency depending on stroke frequency and amplitude (Strouhal-like optimum), fin type (bifins, monofin), leg strength and fatigue; kick timing is a skill input.
- **No-fins technique:** breaststroke cycle with glide; efficiency from timing arm pull and kick coordination.
- **Pool vs open water:** walls/turns in DYN; open-water surface chop interactions at the start/finish.

### 3.2 Buoyancy and pressure
- **Ambient pressure** `P = P0 + ρ g z` (ρ ≈ 1,025 kg/m³ seawater, 1,000 freshwater).
- **Lung volume** `V ∝ 1/P` (Boyle): halves by 10 m; wetsuit neoprene compresses with depth (loss of buoyancy).
- **Net buoyancy** = displaced-water weight − body/gear weight, evolving with lung volume, suit compression and weighting. **Neutral buoyancy depth** (typically ~10-15 m with proper weighting) divides "positive-buoyancy ascent assist" from "free-fall descent". Skill: weighting choice, pacing the descent, and managing the ascent when buoyancy returns.
- **Equalization:** ears (Frenzel/Valsalva) and mask squeeze. A rhythm-based input with a rising difficulty with depth; missed equalizations produce pain, speed limits, injury (barotrauma → dive ends), requiring slower descent and clearing technique.
- **Lung squeeze / mouthfill (advanced):** deferred; flagged as a later-depth mechanic.

### 3.3 Physiology (gameplay model)
A coupled, simplified model - parameters tunable per athlete archetype and calibrated to produce plausible dive durations, **not** a clinical simulation.

| State | Dynamics |
|---|---|
| **O₂ store** (blood + muscle myoglobin + lungs) | Consumption rate = basal + exertion (function of stroke effort and heart rate); reduced by diving response (bradycardia, peripheral vasoconstriction, spleen contraction) |
| **CO₂ / urge-to-breathe** | Rises with metabolic rate; drives involuntary breathing movements (contractions) after a threshold; tolerance trainable (athlete archetype) |
| **Diving response** | Heart-rate reduction increases with cold-water facial immersion, relaxation, and depth; lowers O₂ use |
| **Hypoxia** | Alveolar PO₂ falls non-linearly; at depth it is preserved by pressure, then drops sharply during ascent (blackout risk shows in the last ~10 m) - simulated with partial-pressure scaling |
| **Mental state / relaxation** | A hidden stress variable raised by panic events (missed equalization, current shock, collision) and reduced by calm technique; affects metabolic rate |
| **Narcosis (depth)** | Mild performance effects for deeper dives (reaction noise, judgment) - applied as a subtle input perturbation `[VERIFY plausibility at v1 depths]` |
| **Cold** | Water temperature affects heat loss, shivering, and fatigue |
| **Fatigue** | Leg muscle fatigue lowers thrust efficiency |

**Player-facing feedback (diegetic where possible):** heartbeat and breathing sounds, tunnel vision and color shift near hypoxia, contraction twitches shaking the camera, pulsing peripheral blur, a simple optional sport-watch HUD (depth, time, heart rate), and the dive computer used by real freedivers for depth/time.

**Safety framing:** an on-screen note in the settings/first-run: "This game is a simulation for entertainment. Never practice breath-hold diving alone or without training and supervision."

### 3.4 Flow fields (HRFlow)
- 3-D vector fields: tidal currents, wall upwelling, rip currents, wave-induced surge (oscillatory near-surface motion decaying with depth `e^{-kz}`), cave flow through restrictions, thermoclines (temperature layers).
- **Authoring:** low-resolution grid + analytic functions + noise, precomputed per scenario; sampled deterministically.
- **Gameplay:** use currents to save oxygen; surge can slam a diver into reef; strong flow shifts tags/line.

### 3.5 Visibility and optics (physics-driven)
- **Absorption by wavelength:** red attenuated within ~5-10 m, orange/yellow by ~20-30 m, leaving blue-green; coefficient sets for ocean water types (clear oceanic, coastal, turbid lake) `[VERIFY coefficient sources, e.g. published Jerlov water types]`.
- **Scattering and turbidity:** suspended particulates produce veiling light and reduced contrast; "marine snow".
- **Caustics:** surface wave-driven caustic patterns on the seabed fading with depth; modulated by the HROcean surface.
- **Snell's window:** looking up from below shows the upper hemisphere compressed into a ~97° cone with total internal reflection outside.
- **Mask effects:** field-of-view reduction, magnification from flat mask air-gap (objects appear ~33% closer/larger), fogging, flooding.
- **Cave silt-out:** kicks near silt floors raise particles, reducing visibility locally for a duration - a navigational hazard and a tactical tool.
- **Light shafts** (volumetric) and exposure adaptation.

### 3.6 Determinism
Fixed step (5-10 ms), `double` state, deterministic stroke/physiology models, seeded flow and wave samplers. Rendering effects (particulates, fish) are cosmetic and non-authoritative unless gameplay depends on them (e.g. silt, which is a deterministic field).

---

## 4. Environments

| Environment | Features | Data and art strategy |
|---|---|---|
| **Open-ocean blue-water shaft** (competition line) | Clear, deep, current, thermocline | Procedural water volume; minimal geometry; strong light work |
| **Coral reef wall** | Dense geometry, marine life, current, caustics | PCG corals from scanned/CC assets; reef bathymetry from GEBCO as macro layout |
| **Kelp forest** | Light shafts, surge, entanglement hazards (non-lethal) | Procedural kelp with wave-coupled motion |
| **Wreck site** | Tag objects, penetration (short), silt | Authored hero wrecks |
| **Cenote / flooded cave** | Halocline, guideline, silt, restrictions | Photogrammetry-like assets or procedural karst caves |
| **Pool** | Lane lines, walls | Simple kit |
| **Lake / quarry** | Cold, green, turbid | Water type variation |

Marine life (fish schools, rays, turtles) via Mass/boids: cosmetic ambience with some interactive behaviors (flee when approached).

---

## 5. Rendering

| Element | Approach |
|---|---|
| Water surface from above/below | HROcean surface with refraction, Snell's window, total internal reflection, surface-to-volume transition when the camera crosses |
| Underwater volume | Custom volumetric/post material: wavelength-dependent attenuation, scattering, depth fog, god rays; exposure curve |
| Caustics | Projected from surface normals, animated; fades with depth |
| Particulates | Niagara for marine snow and silt (driven by silt field) |
| Corals/kelp | Nanite/foliage with wind→current-driven vertex animation from HRFlow samples |
| Mask/camera | Mask frame, fogging, droplets, lens distortion |
| Characters | First-person primarily (hands, fins, body shadow); third-person replay with MetaHuman-class avatars in wetsuits (optional) |
| Performance | Underwater volume shaders are fill-rate heavy; budget ≥ 60 FPS at 1080p on Reference tier `[VERIFY S4]` |
| VR (optional later) | Natural fit; separate performance target and comfort design |

---

## 6. Controls and UX

- **Controls (KB/mouse or gamepad):** body pitch/yaw with mouse/stick; kick strokes via timed key/trigger presses (rhythm-based) or analog stick oscillation; arm pull for CNF/FIM; equalize by timed pulse input; relax/streamline toggle; head-up for visual scan; finning amplitude control.
- **Tutorials:** staged dive school: surface breathing and relaxation, duck-dive, equalization rhythm, free-fall, turn, ascent, surface protocol.
- **Difficulty/assists:** assist levels (auto-equalize prompts, kick-timing helper, pre-announced depth), unassisted experts mode.
- **HUD:** minimal; optional dive computer; no health bar. Telemetry post-dive: depth profile, heart rate, O₂ curve, stroke efficiency.
- **Accessibility:** adjustable rhythm tolerances, alternative input for timing, reduced camera shake/tunnel effects, color-blind safe markers.
- **Audio:** bubbles, heartbeat, own breathing/exhalations, muffled speech, pressure creaks, reef sounds (snapping shrimp, distant boats), low-pass filtering by depth and head position; surface sounds change at the interface.

---

## 7. Networking

- **Async-first** (all individual disciplines are verified by replays).
- **Live phase 2:** reef race (parallel instances with light interaction), capture-the-buoy 3v3.
- Water is slow; tick 20-30 Hz; own-diver prediction; other divers interpolated.
- **Spectating:** underwater spectator drone cameras; broadcast director highlights near-blackout moments and surface protocols (competition drama).
- **Replay system:** records inputs and physiology state hashes; supports split-screen comparisons of depth/O₂ curves.

---

## 8. AI and ML

| Use | Approach |
|---|---|
| Ghost divers | Replays |
| Scripted divers | Parametrized archetypes (efficient, aggressive, cautious) |
| Learned divers | RL on the headless sim to learn pacing (descent speed, kick cadence, turn timing) for a given O₂ budget; imitation from human replays |
| Coaching assistant | Post-dive analysis that identifies inefficiencies (e.g. too-early descent kicks, late relaxation) |
| Rating/personalization | Skill estimates per discipline; adaptive training suggestions |
| Evaluation | Bot-versus-bot results; checks that bots cannot violate physiology limits |

---

## 9. Technical architecture

```
DepthCharge (game module)
 ├─ DCDiver        body dynamics, stroke models, equipment/weighting
 ├─ DCPhysio       O2/CO2 model, diving response, hypoxia, mental state
 ├─ DCPressure     pressure, lung volume, buoyancy, equalization system
 ├─ DCWater        optical model parameters, visibility fields, silt field
 ├─ DCCourse       disciplines, lines, tags, scoring, surface protocol
 ├─ DCTeam         3v3 objectives (phase 2)
 ├─ DCAI           scripted/learned divers, coach
 ├─ DCRender       underwater volume, caustics, mask effects, particulate drivers
 └─ DCUI           dive computer, post-dive analytics, tutorials
```
Platform: HRCore, HRScenario, HRReplay, HROcean, HRFlow, HRGeo, HRNet, HRRating, HRTelemetry, HRAgents.

**Data flow:** Scenario (seed, site, discipline, conditions) → flow/visibility/silt fields → diver step (hydro + physio + pressure) → course rules → HRReplay; rendering reads sim state.

---

## 10. Content, data and policy
- **Site data:** bathymetry (GEBCO/NOAA) for macro layout; hero scenes authored. Procedural coral/kelp using CC0/Fab assets.
- **Optical coefficients:** published water-type attenuation data (e.g. Jerlov classes) `[VERIFY]`.
- **Physiology parameters:** from published breath-hold literature at the level of gameplay plausibility; document sources; no claim of medical accuracy.
- **Competition rules:** AIDA-style disciplines described generically; avoid trademark use; surface protocol implemented as a game rule.
- **Safety:** first-run notice, no encouragement of unsafe practice, blackout framed as a loss condition, optional "safety diver" cooperative mode reinforcing buddy practice.
- **Marine life:** no harm-to-animal mechanics; respectful behavior.

---

## 11. Verification strategy
See [SPIKES.md](./SPIKES.md). Summary:

| Layer | Evidence |
|---|---|
| Pressure/buoyancy | Analytic checks: lung volume halves at 10 m; neutral buoyancy depth equals computed value for given weighting |
| Physiology plausibility | Parameter archetypes produce static/dynamic/depth dive durations in plausible ranges (e.g. relaxed static of several minutes; typical depth dives 1.5-4 min) |
| Determinism | Re-sim identical hashes |
| Optical honesty | Rendered color attenuation matches the model's per-wavelength coefficients (measured from captured frames) within tolerance |
| Control feel | Owner playtests on equalization/stroke input; recorded honestly |
| Performance | Frame-time percentiles in worst-case scenes (reef + caustics + particulates) |

---

## 12. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Is "holding your breath" fun to play (pacing/tension)? | High | High | Early prototype of one discipline (CWT) with ghosts; treat as a design experiment; iterate on feedback systems |
| Input design for strokes/equalization feels gimmicky | High | Medium | Prototype multiple input schemes; assists; test with owner |
| Underwater rendering cost/quality | Medium | High | S4 benchmark; stylization within physical constraints |
| Physiology model too complex or unconvincing | Medium | Medium | Keep coupled simple model; tune with archetypes; document limits |
| Safety/responsibility perception | Low | Medium | Safety messaging; no instructions; blackout presented as failure |
| Media/asset volume for reefs and caves | High | Medium | Procedural and kit-based; few hero sites |
| Team mode netcode complexity | Medium | Low (deferred) | Async-first |
| Genre appeal ceiling | Medium | Low (portfolio) | Treat as a high-craft showcase |

---

## 13. Milestones (gated)

| Gate | Deliverable | Exit evidence |
|---|---|---|
| C0 | Spikes S1-S3 | Pressure/buoyancy correct; physiology archetypes plausible; visibility model correct |
| C1 | CWT prototype | One shaft, one discipline, ghost, replay, dive computer |
| C2 | Visual vertical slice | Blue-water + reef wall with caustics/light shafts/marine snow within budget |
| C3 | Disciplines expansion | FIM, CNF, DYN, STA |
| C4 | Verified async leaderboard | Server re-sim |
| C5 | Reef race + currents | HRFlow in play; route choice |
| C6 | Cave swim-through | Silt and guideline mechanics |
| C7 | Team/live (optional) | Capture the buoy tests |

---

## 14. Open decisions

| Decision | Default | Resolve by |
|---|---|---|
| First discipline | Constant Weight with ghost | C0 |
| Input scheme | Rhythm kicks + timed equalize, with assist | C1 |
| VR | Deferred | After C2 |
| Cave scope in v1 | Short swim-through only | C6 |
| Depth cap in v1 | ~60-80 m equivalent shown, no deep-record claims | C1 |
| Co-op safety diver | Post-v1 | After C5 |
