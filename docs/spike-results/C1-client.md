# C1 evidence: playable Constant Weight client (prototype)

**Date:** 2026-11-02. **Code:** `python/depthcharge/play/` (server, session, coach, `static/index.html`). **Tests:** `python/tests/test_play.py` (37 tests in total pass).

## What it is
A real-time 2D side view of one dive: depth scale with a water colour that darkens with depth, a rope with the tag at the announced depth, ear-pressure and urge gauges, a dive-computer readout, tunnel vision and camera shake as the hypoxia and contraction cues, a scripted ghost diver on the same dive, and a debrief with a depth / urge / oxygen plot that releases the hidden oxygen curve only after the dive. A *Guided practice dive* (trained diver, 20 m, fixed seed) shows one hint at a time from the diver's own observation. Oxygen and CO2 are never sent during the dive (tested).

## Verified
- A proxy player using only the client's coarse controls (kick, hard kick, nothing, plus the pulse keys) completes the guided dive through the HTTP layer and the replay verifies; the coach shows every stage in order (dive, equalize, reach the tag, turn, surface protocol).
- Bad requests are rejected; the replay is withheld until the dive has ended; the real HTTP server serves the page.

## Not verified
- **Nobody has played it, and it has not been viewed in a browser** (no browser tool was available when it was written). Layout, readability and feel are unknown. The page's JavaScript parses; that is all.
- Whether the keyboard controls (hold Space, tap E in a gauge window) are fun or fiddly, and whether the equalization window and the 3-second turn feel fair: SPIKES S6 and S10 are open and need the owner.
- Real-time pacing depends on the browser timer; the clock follows wall time (up to 0.3 s per request).
