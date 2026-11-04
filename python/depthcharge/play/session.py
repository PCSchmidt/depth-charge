"""One human-played dive. The session is the harness side: it releases truth (O2, CO2 curves) only after the dive ends."""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import model as M
from ..bots import DynDiver, ScriptedDiver
from ..dive import ARCHETYPES, DISCIPLINE_LEAD, DISCIPLINES, PROTOCOL, PULSES, Dive, Scenario, replay, run
from .coach import coach, coach_dyn

PLAIN = {
    "success": "Dive completed: you reached the tag, came back and passed the surface protocol.",
    "blackout": "Blackout: your oxygen ran out before you reached the surface. In this game that is a loss, not a goal.",
    "no_tag": "You surfaced without the tag, so the dive does not count.",
    "protocol_failed": "You missed a surface-protocol deadline, which voids the dive.",
    "barotrauma": "Ear injury: you went too long without equalizing. The dive ends (safe recovery).",
    "timeout": "The dive timed out.",
    "short": "You stopped before the distance you announced, so the swim does not count.",
}
# scripted-diver settings per discipline: (kick frequency, speed m/s). The ghost and the proxy players use these.
GHOST = {"CWT": (0.8, 0.75), "FIM": (0.35, 0.6), "CNF": (0.3, 0.5)}
PRACTICE = dict(seed=5, archetype="trained", announced_depth_m=20.0, lead_kg=1.2)


@dataclass
class Session:
    sc: Scenario
    guided: bool = False
    dive: Dive = field(init=False)
    ghost: list = field(init=False)
    samples: list = field(init=False, default_factory=list)

    def __post_init__(self):
        self.dive = Dive(self.sc)
        g = run(self.sc, _bot(self.sc))                                 # the ghost: the scripted diver on the same scenario
        self.ghost = _ghost_path(self.sc)
        self.ghost_outcome = g.outcome
        self.ghost_time = g.t

    @property
    def neutral_m(self):
        if self.sc.discipline == "DYN":
            return None
        return M.neutral_depth(ARCHETYPES[self.sc.archetype].lung_l / 1000.0, self.sc.lead_kg, self.sc.rho)

    def step(self, n: int, change: dict | None) -> None:
        d = self.dive
        want = change or {}
        first = {k: v for k, v in want.items() if (k in PULSES and v) or (k not in PULSES and d.controls.get(k) != v)}
        for i in range(max(1, min(int(n), 40))):
            if d.ended:
                break
            d.step(first if i == 0 and first else None)
            if d.tick % int(round(1.0 / self.sc.dt)) == 0:
                self.samples.append([round(d.t, 1), round(d.dist if self.sc.discipline == "DYN" else d.z, 2), round(min(1.2, max(0.0, (d.co2 - 40.0) / (d.arch.c_break_mmhg - 40.0))), 3),
                                     round(d.pao2(), 4)])

    def state(self) -> dict:
        d = self.dive
        ob = d.observation()
        out = {"observation": ob, "scenario": {"announced_depth_m": self.sc.announced_depth_m, "archetype": self.sc.archetype, "lead_kg": self.sc.lead_kg,
                                                 "dt": self.sc.dt, "seed": self.sc.seed, "neutral_depth_m": self.neutral_m,
                                                 "discipline": self.sc.discipline, "stroke_f": M.STROKES[self.sc.discipline][0],
                                                 "announced_distance_m": self.sc.announced_distance_m, "pool_m": self.sc.pool_m},
               "events": [e for e in d.events if not e[1].startswith("eq_")][-6:], "eq": {"ok": d.eq_ok, "failed": sum(1 for e in d.events if e[1] == "eq_failed")},
               "last_eq": next(([e[0], e[1]] for e in reversed(d.events) if e[1].startswith("eq_")), None),
               "protocol": [list(p) for p in PROTOCOL]}
        if self.sc.discipline == "DYN":
            out["coach"] = coach_dyn(ob, self.sc.announced_distance_m, self.sc.pool_m)
        elif self.guided or self.sc.discipline != "CWT":
            out["coach"] = coach(ob, self.sc.announced_depth_m, self.neutral_m)
        if d.ended:
            out["debrief"] = self.debrief()
        return out

    def debrief(self) -> dict:
        d = self.dive
        r = replay(self.sc, d.log)
        ev = [e[1] for e in d.events]
        return {"outcome": d.outcome, "plain": PLAIN.get(d.outcome, d.outcome), "score": d.score, "time_s": round(d.t, 1),
                "verified": r.digest() == d.digest(), "digest": d.digest(), "samples": self.samples,
                "eq": {"ok": ev.count("eq_ok"), "failed": ev.count("eq_failed"), "early": ev.count("eq_early"), "locked": ev.count("eq_locked")},
                "contractions": "contractions" in ev, "samba": d.samba, "min_pao2": round(d.min_pao2, 3),
                "ghost": {"time_s": round(self.ghost_time, 1), "outcome": self.ghost_outcome}, "events": d.events}

    def replay_json(self) -> dict:
        if not self.dive.ended:
            raise PermissionError("replay is released when the dive has ended")
        return {"scenario": self.sc.__dict__, "log": self.dive.log, "digest": self.dive.digest()}


def _bot(sc: Scenario):
    if sc.discipline == "DYN":
        return DynDiver(sc.announced_distance_m, pool_m=sc.pool_m)
    f, sp = GHOST.get(sc.discipline, GHOST["CWT"])
    return ScriptedDiver(sc.announced_depth_m, descent_mps=sp, ascent_mps=sp, kick_f=f)


def _ghost_path(sc: Scenario) -> list:
    bot = _bot(sc)
    d = Dive(sc)
    path, step = [], max(1, int(round(0.5 / sc.dt)))
    pos = (lambda: d.x) if sc.discipline == "DYN" else (lambda: d.z)      # DYN ghost: position along the pool
    for i in range(int(sc.max_time_s / sc.dt) + 2):
        if d.ended:
            break
        if i % step == 0:
            path.append([round(d.t, 2), round(pos(), 2)])
        want = bot(d.observation()) or {}
        d.step({k: v for k, v in want.items() if (k in PULSES and v) or (k not in PULSES and d.controls.get(k) != v)} or None)
    path.append([round(d.t, 2), round(pos(), 2)])
    return path


def new_session(archetype="trained", depth=20.0, lead=1.2, seed=None, guided=False, discipline="CWT", distance=75.0) -> Session:
    import random
    if guided:
        return Session(Scenario(**PRACTICE), guided=True)
    if discipline not in DISCIPLINES or discipline == "STA":
        raise ValueError("discipline must be CWT, FIM, CNF or DYN")
    return Session(Scenario(seed=seed if seed is not None else random.randrange(1, 2**31), archetype=archetype, discipline=discipline,
                            announced_depth_m=20.0 if discipline == "DYN" else float(depth), announced_distance_m=float(distance), lead_kg=float(lead)))
