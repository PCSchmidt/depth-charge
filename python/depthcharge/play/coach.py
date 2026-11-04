"""Guided-practice coach: one hint at a time, computed only from what the diver could feel or read (the observation)."""
from __future__ import annotations

KEYS = {"remove_mask": ("M", "remove your mask"), "ok_sign": ("O", "give the OK sign"), "speak_ok": ("V", "say \"I'm OK\"")}


def coach(ob: dict, announced_m: float, neutral_m: float | None) -> dict:
    z, ex = ob["depth_m"], ob["ear_excess"]
    zn = neutral_m if neutral_m is not None else 0.0
    if ob["ended"]:
        return {"title": "Dive over", "text": "Read the debrief below the gauges.", "urgent": False}
    if ob["surfaced"]:
        step = ob["protocol_next"]
        k, what = KEYS[step]
        return {"title": "Surface protocol", "urgent": ob["protocol_left_s"] < 6.0,
                "text": f"You are up. Hold B to breathe, then press {k} to {what} ({ob['protocol_left_s']:.0f} s left). Steps in order: M, then O, then V. Missing a deadline voids the dive."}
    if ob["tunnel_vision"] > 0.2 and ob["has_tag"]:
        return {"title": "Tunnel vision", "urgent": True,
                "text": "Your vision is closing in: oxygen is low and it gets worse as you rise. Keep moving up steadily; do not stop or turn back."}
    if ex >= 0.12 and ob["dir"] == 1:
        return {"title": "Ear pain", "urgent": True, "text": "Your ears hurt. Press E now. If it fails, stop descending (let yourself rise a little) and try again; at 20% they lock."}
    if ex >= 0.04 and ob["dir"] == 1 and not ob["has_tag"]:
        return {"title": "Equalize", "urgent": ex >= 0.09, "text": "The ear gauge is in the green. Press E to equalize. Too early (grey zone) wastes the press; too late (red) risks pain."}
    if z < 1.0 and ob["dir"] == 1 and not ob["has_tag"] and ob["t"] < 1.0:
        return {"title": "1. Dive", "urgent": False,
                "text": "Hold Space to kick down; hold K for a harder kick. Near the surface you float, so kick hard until you pass your neutral depth."}
    if ob["dir"] == 1 and not ob["has_tag"]:
        if z >= announced_m - 3.0:
            return {"title": "3. Reach the tag", "urgent": False,
                    "text": f"The tag is at {announced_m:.0f} m (orange). Press G when you are at or below {announced_m - 0.5:.1f} m. Then turn with T."}
        if z < zn - 0.5 or ob["net_up_n"] > 5.0:
            return {"title": "2. Keep kicking", "urgent": False,
                    "text": f"You are still floating up (+{ob['net_up_n']:.0f} N). Past your neutral depth (about {zn:.0f} m) you sink on your own, so kicking costs oxygen for nothing."}
        return {"title": "2. Free fall", "urgent": False,
                "text": "You are sinking by yourself. Let go of Space, stay streamlined and relax: calm saves oxygen. Press E whenever the ear gauge is green."}
    if ob["dir"] == 1 and ob["has_tag"]:
        return {"title": "4. Turn", "urgent": False, "text": "You have the tag. Press T to turn head-up (about 1.5 s, no thrust). Then HOLD K or Space to swim up."}
    if ob["turning"]:
        return {"title": "4. Turning", "urgent": False, "text": f"Turning ({ob['turn_left_s']:.1f} s)... then HOLD K or Space to swim up."}
    if z > zn:
        return {"title": "5. Kick up", "urgent": False, "text": f"Swim up now: HOLD K (hard) or Space. You are heavy at this depth, so it takes a few seconds to start rising. Above about {zn:.0f} m you float up on your own."}
    return {"title": "5. Float up", "urgent": False,
            "text": "You are positively buoyant now: you rise by yourself. Relax; kick only if you slow down. Hold B once your head is out."}


def coach_dyn(ob: dict, goal_m: float, pool_m: float) -> dict:
    """Hints for Dynamic apnea in a pool: swim, turn at the walls, finish once the announced distance is covered."""
    if ob["ended"]:
        return {"title": "Swim over", "text": "Read the debrief below the gauges.", "urgent": False}
    if ob["surfaced"]:
        k, what = KEYS[ob["protocol_next"]]
        return {"title": "Surface protocol", "urgent": ob["protocol_left_s"] < 6.0,
                "text": f"Hold B to breathe, then press {k} to {what} ({ob['protocol_left_s']:.0f} s left). Steps in order: M, then O, then V."}
    if ob["turning"]:
        return {"title": "Turning", "urgent": False, "text": f"Turning at the wall ({ob['turn_left_s']:.1f} s), then hold K or Space to push off and swim back."}
    if ob["distance_m"] >= goal_m:
        return {"title": "Goal reached", "urgent": ob["urge"] > 0.8,
                "text": "You have covered the announced distance. Press F to stop and surface, then breathe (B) and do the surface protocol (M, O, V). Swimming further adds to your score but risks a blackout."}
    at_wall = (ob["x_m"] >= pool_m - 0.3 and ob["dir"] == 1) or (ob["x_m"] <= 0.3 and ob["dir"] == -1)
    if at_wall and ob["t"] > 2.0:
        return {"title": "Wall", "urgent": False, "text": "You are at the wall. Press T to turn and push off."}
    return {"title": "Swim", "urgent": ob["urge"] > 0.8,
            "text": f"Hold Space (or K for harder) to swim. {ob['distance_m']:.0f} of {goal_m:.0f} m. Press T at each wall to turn. Calm, steady swimming saves oxygen."}
