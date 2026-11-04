"""One diver, one dive: Constant Weight (CWT) with a tag and surface protocol, or a Static (STA) breath-hold.

Deterministic: the only randomness is a seeded generator consumed when an equalization is attempted. The physiology is a
coupled gameplay model (SPEC 3.3); parameters are design values chosen to give plausible durations, not medical data.
"""
from __future__ import annotations

import hashlib
import math
import random
import struct
from dataclasses import dataclass, field

from . import model as M

# ---- physiology design values --------------------------------------------------------------------------------
FA0 = 0.15                   # usable lung O2 fraction at the start of the dive (before any use)
BLACKOUT_PAO2 = 0.04         # atm; below this the diver loses consciousness
SAMBA_PAO2 = 0.06            # atm; below this on the way up the dive is penalised ("hypoxic samba")
C0 = 40.0                    # mmHg-like CO2 tension at the start
K_C = 0.018                  # CO2 tension rise per mL of O2 consumed
C_WORK = 1500.0              # extra mL/min of O2 per unit effort squared (effort = amplitude * kick frequency)
SURFACE_REFILL = 60.0        # mL/s of O2 store recovered while breathing at the surface
TURN_S = 1.5                    # s: no thrust while the diver rotates (playtest: 3 s felt slow)
EAR_PAIN = 0.12              # ambient/ear pressure ratio excess at which equalizing hurts
EAR_LOCK = 0.20              # beyond this the tubes lock: equalizing is impossible
EAR_INJURY = 0.35            # beyond this the dive ends (barotrauma)
PROTOCOL = (("remove_mask", 15.0), ("ok_sign", 20.0), ("speak_ok", 30.0))   # (step, deadline in s after surfacing)
MAX_ANNOUNCED_M = 40.0       # lung squeeze is not modelled (SPEC 3.2), so the depth is capped where lungs reach ~1.2 L


@dataclass(frozen=True)
class Archetype:
    name: str
    o2_store_ml: float       # usable body O2 at the start of the dive
    basal_ml_min: float      # resting O2 use
    dr_max: float            # maximum diving-response reduction in O2 use
    c_break_mmhg: float      # CO2 tension at which the urge to breathe becomes unmanageable
    thrust_max_n: float
    eq_fail: float           # chance an equalization attempt fails when well timed
    lung_l: float            # lung gas at the surface


ARCHETYPES = {
    "novice": Archetype("novice", 1300.0, 280.0, 0.15, 50.0, 70.0, 0.12, 5.5),
    "trained": Archetype("trained", 1600.0, 250.0, 0.30, 56.0, 90.0, 0.04, 6.0),
    "elite": Archetype("elite", 1900.0, 220.0, 0.40, 63.0, 110.0, 0.01, 6.5),
}


@dataclass(frozen=True)
class Scenario:
    seed: int = 1
    archetype: str = "trained"
    discipline: str = "CWT"          # "CWT" or "STA"
    announced_depth_m: float = 20.0
    lead_kg: float = 1.2
    dt: float = 0.05                 # s; the spec asks for 5-10 ms, 50 ms keeps the Python prototype fast (see docs)
    max_time_s: float = 600.0
    rho: float = M.RHO_SEA

    def validate(self) -> None:
        if self.archetype not in ARCHETYPES:
            raise ValueError(f"archetype must be one of {sorted(ARCHETYPES)}")
        if self.discipline not in ("CWT", "STA"):
            raise ValueError("discipline must be CWT or STA")
        if not 5.0 <= self.announced_depth_m <= MAX_ANNOUNCED_M:
            raise ValueError(f"announced depth must be 5-{MAX_ANNOUNCED_M:.0f} m")
        if not 0.0 <= self.lead_kg <= 8.0:
            raise ValueError("lead must be 0-8 kg")
        if not 0.005 <= self.dt <= 0.1:
            raise ValueError("dt must be 5-100 ms")


DEFAULT_CONTROLS = {"dir": 1, "f": 0.0, "a": 0.0, "streamline": True, "face_down": False}
PULSES = ("equalize", "breathe", "grab_tag", "remove_mask", "ok_sign", "speak_ok")   # one-tick actions, never persistent


@dataclass
class Dive:
    sc: Scenario
    t: float = 0.0
    tick: int = 0
    z: float = 0.0
    v: float = 0.0
    dir: int = 1
    turn_lock: float = 0.0
    o2: float = 0.0
    co2: float = C0
    stress: float = 0.0
    fatigue: float = 0.0
    t_sub: float = 0.0
    p_ear: float = M.P0
    has_tag: bool = False
    went_deep: bool = False
    breathing: bool = False
    surfaced_at: float | None = None
    protocol_done: int = 0
    contractions: bool = False
    urge_limit: bool = False
    samba: bool = False
    min_pao2: float = 1.0
    eq_ok: int = 0
    outcome: str | None = None
    score: float = 0.0
    events: list = field(default_factory=list)
    controls: dict = field(default_factory=lambda: dict(DEFAULT_CONTROLS))
    log: list = field(default_factory=list)          # [tick, controls and pulses given at this tick]
    _h: object = field(default_factory=hashlib.sha256, repr=False)

    def __post_init__(self):
        self.sc.validate()
        self.arch = ARCHETYPES[self.sc.archetype]
        self.rng = random.Random(self.sc.seed)
        self.o2 = self.arch.o2_store_ml
        self.v_lung = self.arch.lung_l / 1000.0
        self.mass_eff = M.BODY_MASS + M.SUIT_MASS + self.sc.lead_kg + M.ADDED_MASS
        self.c_cont = C0 + 0.6 * (self.arch.c_break_mmhg - C0)

    # ---- derived, player-visible quantities --------------------------------------------------------------
    @property
    def ended(self) -> bool:
        return self.outcome is not None

    def pao2(self) -> float:
        return FA0 * max(self.o2, 0.0) / self.arch.o2_store_ml * M.pressure(self.z, self.sc.rho) / M.P0

    def ear_excess(self) -> float:
        return M.pressure(self.z, self.sc.rho) / self.p_ear - 1.0

    def net_up_n(self) -> float:
        return M.net_buoyancy_force(self.z, self.v_lung, self.sc.lead_kg, self.sc.rho)

    def next_protocol_step(self):
        if self.surfaced_at is None or self.protocol_done >= len(PROTOCOL):
            return None
        return PROTOCOL[self.protocol_done][0]

    def observation(self) -> dict:
        """What a diver could feel or read on a dive computer. True O2 and CO2 are deliberately absent."""
        arch = self.arch
        step = self.next_protocol_step()
        left = self.surfaced_at + PROTOCOL[self.protocol_done][1] - self.t if step else None
        return {"t": self.t, "tick": self.tick, "depth_m": self.z, "vertical_speed_mps": self.v, "dir": self.dir,
                "ear_excess": self.ear_excess(), "has_tag": self.has_tag, "contractions": self.contractions,
                "urge": min(1.2, max(0.0, (self.co2 - C0) / (arch.c_break_mmhg - C0))),
                "tunnel_vision": min(1.0, max(0.0, (0.09 - self.pao2()) / 0.05)), "net_up_n": self.net_up_n(),
                "turning": self.turn_lock > 0.0, "turn_left_s": round(self.turn_lock, 2), "surfaced": self.surfaced_at is not None,
                "protocol_next": step, "protocol_left_s": left, "stress": self.stress,
                "ended": self.ended, "outcome": self.outcome}

    def truth(self) -> dict:
        return {"o2_ml": self.o2, "co2": self.co2, "pao2_atm": self.pao2(), "fatigue": self.fatigue, "min_pao2": self.min_pao2}

    # ---- stepping ---------------------------------------------------------------------------------------
    def _event(self, name: str) -> None:
        self.events.append((round(self.t, 3), name))

    def _end(self, outcome: str, score: float = 0.0) -> None:
        self.outcome, self.score = outcome, score
        self._event(outcome)

    def step(self, change: dict | None = None) -> None:
        if self.ended:
            return
        sc, arch, dt = self.sc, self.arch, self.sc.dt
        pulses: dict = {}
        if change:
            self.log.append([self.tick, dict(change)])
            for k, val in change.items():
                if k in PULSES:
                    pulses[k] = val
                elif k in DEFAULT_CONTROLS:
                    self.controls[k] = val
                else:
                    raise ValueError(f"unknown control {k!r}")
        c = self.controls
        want_dir = 1 if c["dir"] >= 0 else -1
        if want_dir != self.dir and self.turn_lock <= 0.0:
            self.dir, self.turn_lock = want_dir, TURN_S
        self.turn_lock = max(0.0, self.turn_lock - dt)
        turning = self.turn_lock > 0.0
        on_surface = self.z <= 0.3

        # -- propulsion and motion (1-D along the line) --
        f, a = min(max(float(c["f"]), 0.0), 1.6), min(max(float(c["a"]), 0.0), 1.0)
        thrust = 0.0 if turning else M.kick_thrust(arch.thrust_max_n, f, a, self.fatigue) * (0.7 if self.urge_limit else 1.0)
        effort = 0.0 if turning else a * f
        cda = M.CDA_STREAMLINED if (c["streamline"] and not turning) else M.CDA_BROADSIDE
        down = -self.net_up_n() + self.dir * thrust - M.drag(self.v, cda, sc.rho)
        self.v += down / self.mass_eff * dt
        self.z += self.v * dt
        if self.z < 0.0:
            self.z, self.v = 0.0, max(self.v, 0.0)
        if self.z > 1.0:
            self.went_deep = True
        self.t += dt
        self.tick += 1

        # -- physiology --
        relax = min(1.0, max(0.3, 1.0 - 2.0 * effort)) * (1.0 if c["streamline"] else 0.8)
        submerged = self.z > 0.5 or bool(c["face_down"])
        self.t_sub = self.t_sub + dt if submerged else max(0.0, self.t_sub - 3.0 * dt)
        dr = arch.dr_max * (1.0 - math.exp(-self.t_sub / 40.0)) * relax * (1.0 - 0.5 * self.stress)
        vo2 = arch.basal_ml_min * (1.0 + 0.4 * self.stress) * (1.0 - dr) + C_WORK * effort * effort * (1.0 + 0.3 * self.fatigue)
        if not on_surface:
            self.breathing = False
        elif pulses.get("breathe"):
            self.breathing = True
        if self.breathing:
            self.o2 = min(arch.o2_store_ml, self.o2 + SURFACE_REFILL * dt)
            self.co2 = max(C0, self.co2 - 1.5 * dt)
        else:
            self.o2 -= vo2 / 60.0 * dt
            self.co2 += K_C * vo2 / 60.0 * dt
        self.fatigue = min(1.0, max(0.0, self.fatigue + (0.02 * effort * effort - 0.01 * self.fatigue) * dt))
        if self.co2 >= self.c_cont and not self.contractions:
            self.contractions = True
            self._event("contractions")
        if self.contractions:
            self.stress = min(1.0, self.stress + 0.003 * dt)
        if self.co2 >= arch.c_break_mmhg and not self.urge_limit:
            self.urge_limit = True
            self._event("urge_limit")
        if self.urge_limit:
            self.stress = min(1.0, self.stress + 0.02 * dt)
        if relax > 0.7 and not self.contractions:
            self.stress = max(0.0, self.stress - 0.02 * dt)

        # -- ears --
        amb = M.pressure(self.z, sc.rho)
        self.p_ear = min(self.p_ear, amb)             # on the way up the ears vent by themselves
        d = amb / self.p_ear - 1.0
        if pulses.get("equalize") and self.z > 0.5:
            if d < 0.02:
                self._event("eq_early")
            elif d > EAR_LOCK:
                self.stress = min(1.0, self.stress + 0.1)
                self._event("eq_locked")
            elif self.rng.random() < arch.eq_fail * (1.0 + 3.0 * self.stress) * (1.0 + self.z / 25.0) + max(0.0, d - EAR_PAIN) * 3.0:
                self.stress = min(1.0, self.stress + 0.05)
                self._event("eq_failed")
            else:
                self.p_ear, self.eq_ok = amb, self.eq_ok + 1
                self._event("eq_ok")
        if d > EAR_PAIN:
            self.stress = min(1.0, self.stress + 0.02 * dt)
            if not any(e[1] == "ear_pain" for e in self.events):
                self._event("ear_pain")
        if d > EAR_INJURY:
            return self._end("barotrauma")

        # -- hypoxia --
        p = self.pao2()
        if self.went_deep:
            self.min_pao2 = min(self.min_pao2, p)
        if self.has_tag and self.dir == -1 and p < SAMBA_PAO2 and not self.samba:
            self.samba = True
            self._event("samba")
        if p < BLACKOUT_PAO2:
            return self._end("blackout")

        # -- rules --
        if sc.discipline == "STA":
            if self.urge_limit:
                return self._end("static_break", self.t)
        else:
            self._cwt_rules(pulses)
        if not self.ended and self.t >= sc.max_time_s:
            self._end("timeout")
        if self.tick % 20 == 0:
            self._h.update(struct.pack("<7d", self.t, self.z, self.v, self.o2, self.co2, self.stress, self.p_ear))

    def _cwt_rules(self, pulses: dict) -> None:
        sc = self.sc
        if pulses.get("grab_tag") and not self.has_tag and self.z >= sc.announced_depth_m - 0.5:
            self.has_tag = True
            self._event("tag")
        if self.surfaced_at is None:
            if self.went_deep and self.z <= 0.1 and self.dir == -1:
                self.surfaced_at = self.t
                self._event("surfaced")
                if not self.has_tag:
                    self._end("no_tag")
            return
        step, deadline = PROTOCOL[self.protocol_done]
        if pulses.get(step):
            self.protocol_done += 1
            self._event(f"protocol_{step}")
            if self.protocol_done == len(PROTOCOL):
                self._end("success", max(0.0, sc.announced_depth_m - (10.0 if self.samba else 0.0)))
        elif self.t - self.surfaced_at > deadline:
            self._end("protocol_failed")

    def digest(self) -> str:
        h = self._h.copy()
        h.update(struct.pack("<7d", self.t, self.z, self.v, self.o2, self.co2, self.stress, self.p_ear))
        h.update(repr((self.outcome, self.score, self.events)).encode())
        return h.hexdigest()[:16]


def run(sc: Scenario, driver) -> Dive:
    """Play a dive: driver(observation) -> controls and pulses given this tick (or None)."""
    d = Dive(sc)
    for _ in range(int(sc.max_time_s / sc.dt) + 2):
        if d.ended:
            break
        want = driver(d.observation()) or {}
        # persistent controls are sent only when they change, pulses whenever they fire: that is the replay log
        d.step({k: v for k, v in want.items() if (k in PULSES and v) or (k not in PULSES and d.controls.get(k) != v)} or None)
    return d


def replay(sc: Scenario, log: list) -> Dive:
    """Re-simulate from the controls log alone."""
    d = Dive(sc)
    by_tick = {t: c for t, c in log}
    for tick in range(int(sc.max_time_s / sc.dt) + 2):
        if d.ended:
            break
        d.step(by_tick.get(tick))
    return d


def verify(sc: Scenario, log: list, claimed_digest: str) -> bool:
    """FR-021/US-3: a submitted dive is accepted only if re-simulating its log reproduces the claimed result."""
    try:
        return replay(sc, log).digest() == claimed_digest
    except (ValueError, TypeError, KeyError):
        return False
