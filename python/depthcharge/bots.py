"""Scripted divers (FR-040): they see only the observation a diver would have, never the true O2 or CO2."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScriptedDiver:
    announced_depth_m: float
    descent_mps: float = 0.75       # target speed while kicking down
    ascent_mps: float = 0.75
    kick_f: float = 0.8             # Hz
    eq_at: float = 0.07            # equalize once the ear pressure excess reaches this
    protocol_delay_s: float = 3.0   # pause between surface protocol steps
    abort_urge: float | None = None  # turn back early when the urge to breathe passes this (None: never)

    def __post_init__(self):
        self._last = None

    def _kick(self, speed_err: float) -> dict:
        a = min(1.0, max(0.0, 0.25 + 1.2 * speed_err)) if speed_err > 0.0 else 0.0
        return {"f": self.kick_f if a > 0.0 else 0.0, "a": a}

    def __call__(self, ob: dict) -> dict | None:
        out: dict = {}
        z, v = ob["depth_m"], ob["vertical_speed_mps"]
        if ob["surfaced"]:
            out["breathe"] = True
            out.update({"f": 0.0, "a": 0.0})
            step = ob["protocol_next"]
            if self._last is None:
                self._last = ob["t"]
            if step is not None and ob["t"] - self._last >= self.protocol_delay_s:
                out[step] = True
                self._last = ob["t"]
            return out
        if z > 0.5 and ob["ear_excess"] >= self.eq_at and not ob["turning"]:
            out["equalize"] = True
        want_up = ob["has_tag"] or (self.abort_urge is not None and ob["urge"] >= self.abort_urge)
        if not want_up:
            out["dir"] = 1
            if z >= self.announced_depth_m - 0.4:
                out["grab_tag"] = True
                out["dir"] = -1
                out.update({"f": 0.0, "a": 0.0})
            else:
                out.update(self._kick(self.descent_mps - v))
        else:
            out["dir"] = -1
            if ob["turning"]:
                out.update({"f": 0.0, "a": 0.0})
            else:
                out.update(self._kick(self.ascent_mps + v))     # v is negative while rising
        return out


def static_hold(ob: dict) -> dict | None:
    """Static apnea: face down, motionless."""
    return {"face_down": True, "f": 0.0, "a": 0.0} if ob["tick"] == 0 else None
