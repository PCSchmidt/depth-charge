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
        return {"title": "4. Turn", "urgent": False, "text": "You have the tag. Press T to turn head-up; turning takes 3 seconds with no thrust."}
    if ob["turning"]:
        return {"title": "4. Turning", "urgent": False, "text": "Turning... wait for it."}
    if z > zn:
        return {"title": "5. Kick up", "urgent": False, "text": f"Hold Space to swim up. Above about {zn:.0f} m you will float up on your own."}
    return {"title": "5. Float up", "urgent": False,
            "text": "You are positively buoyant now: you rise by yourself. Relax; kick only if you slow down. Hold B once your head is out."}
