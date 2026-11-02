"""S2 (archetype plausibility) and S8 (determinism, replay verification)."""
import pytest

from depthcharge.bots import ScriptedDiver, static_hold
from depthcharge.dive import Scenario, replay, run, verify

STATIC_RANGES_MIN = {"novice": (1.0, 2.5), "trained": (3.0, 6.0), "elite": (7.0, 20.0)}     # SPIKES S2
SAFE_DEPTHS = {"novice": (20, 30), "trained": (20, 30, 40), "elite": (20, 30, 40)}


@pytest.mark.parametrize("arch", STATIC_RANGES_MIN)
def test_s2_static_times_and_contraction_onset(arch):
    d = run(Scenario(archetype=arch, discipline="STA", max_time_s=1800.0), static_hold)
    assert d.outcome == "static_break"
    lo, hi = STATIC_RANGES_MIN[arch]
    assert lo <= d.t / 60.0 <= hi
    onset = next(t for t, e in d.events if e == "contractions")
    assert 0.5 <= onset / d.t <= 0.7                         # contractions begin at 50-70% of the maximum time


@pytest.mark.parametrize("arch", SAFE_DEPTHS)
def test_s2_depth_dives_are_ninety_seconds_to_three_minutes_and_do_not_black_out(arch):
    for depth in SAFE_DEPTHS[arch]:
        d = run(Scenario(archetype=arch, announced_depth_m=depth), ScriptedDiver(depth))
        assert d.outcome == "success", (arch, depth, d.events[-3:])
        if depth >= 30:
            assert 90.0 <= d.t <= 180.0, (arch, depth, d.t)


def test_s2_blackout_happens_only_when_the_limits_are_exceeded():
    d = run(Scenario(archetype="novice", announced_depth_m=40), ScriptedDiver(40))      # beyond what a novice can do
    assert d.outcome == "blackout" and d.truth()["pao2_atm"] < 0.04
    safe = run(Scenario(archetype="trained", announced_depth_m=30), ScriptedDiver(30))
    assert safe.min_pao2 > 0.06                                # a comfortable dive never reaches the samba zone


def test_relaxed_diver_uses_less_oxygen_than_a_tense_one():
    used = {}
    for kind, streamline in (("relaxed", True), ("tense", False)):
        d = run(Scenario(archetype="trained", discipline="STA", max_time_s=120.0),
                lambda ob, s=streamline: {"face_down": True, "streamline": s, "f": 0.0, "a": 0.0} if ob["tick"] == 0 else None)
        used[kind] = 1600.0 - d.o2
    assert used["relaxed"] < used["tense"]


def test_s8_same_scenario_and_inputs_give_identical_digests_and_replays_verify():
    sc = Scenario(seed=7, archetype="trained", announced_depth_m=30)
    a, b = run(sc, ScriptedDiver(30)), run(sc, ScriptedDiver(30))
    assert a.digest() == b.digest() and a.log == b.log
    r = replay(sc, a.log)
    assert r.digest() == a.digest() and r.outcome == a.outcome and verify(sc, a.log, a.digest())


def test_s8_different_seed_changes_equalization_luck_but_replays_stay_exact():
    outs = {}
    for seed in (1, 2, 3):
        sc = Scenario(seed=seed, archetype="novice", announced_depth_m=20)
        d = run(sc, ScriptedDiver(20))
        outs[seed] = d.digest()
        assert verify(sc, d.log, d.digest())
    assert len(set(outs.values())) > 1


def test_tampered_logs_are_rejected():
    sc = Scenario(seed=3, archetype="trained", announced_depth_m=30)
    d = run(sc, ScriptedDiver(30))
    good = d.digest()
    dropped = [e for e in d.log if "equalize" not in e[1]]
    assert dropped != d.log and not verify(sc, dropped, good)                         # an equalization removed
    boosted = [[t, ({**c, "a": 1.0, "f": 0.8} if "a" in c else c)] for t, c in d.log]
    assert not verify(sc, boosted, good)                                              # stronger kicks than were played
    assert not verify(sc, [[0, {"warp": 1}]], good)                                   # unknown control


def test_scenario_validation():
    for bad in (dict(announced_depth_m=80), dict(lead_kg=20), dict(archetype="x"), dict(dt=1.0), dict(discipline="DYN")):
        with pytest.raises(ValueError):
            Scenario(**bad).validate()
