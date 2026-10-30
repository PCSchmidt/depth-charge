# Depth Charge - Agent Layer (minimal scope)

**Status:** Draft v1 - design only. Smallest agent scope of the four titles. Reuses the Dark Fleet harness and rules ([Dark Fleet AGENTS.md](https://github.com/PCSchmidt/dark-fleet/blob/main/docs/AGENTS.md)): agents are optional, replay-grounded and act only through the typed, role-limited API.

## 1. Agent
| Agent | Mode | Tools | Output |
|---|---|---|---|
| **Dive Coach** | Post-dive | `get_profile`, `get_events`, `get_stroke_stats`, `get_physio_curves`, `compare_to_reference_profile` | A short review citing event IDs (late equalization, over-kicking, late relaxation, ascent pacing); suggestions for practice drills |

## 2. Safety constraints for the agent
- The coach must not give real-world diving advice or training instructions. Its prompts, tool outputs and response checker restrict content to in-game technique; a safety-notice reminder is shown when users ask real-world questions.
- Output checker rejects medical claims and unsafe-practice encouragement; this is evaluated in a red-team set.

## 3. Evaluation
Faithfulness (cited event IDs exist and support the claim), safety-filter pass rate on a red-team set, usefulness (owner-reviewed), cost and latency. Small fixed seed set; results with confidence intervals.

## 4. Risk
Perceived authority on a safety-related topic: mitigated by scope limits, labelling and the checker.
