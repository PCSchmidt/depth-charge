"""C3: Free Immersion (FIM), Constant No-Fins (CNF) and Dynamic (DYN) on top of the C0 model."""
import random

import pytest

from depthcharge import model as M
from depthcharge.bots import DynDiver, ScriptedDiver
from depthcharge.dive import DISCIPLINE_LEAD, DISCIPLINES, Scenario, replay, run, verify


def line_dive(disc, arch, depth, seed=3):
    f, sp = {"FIM": (0.35, 0.6), "CNF": (0.3, 0.5)}[disc]
    sc = Scenario(seed=seed, archetype=arch, discipline=disc, announced_depth_m=depth, lead_kg=DISCIPLINE_LEAD[disc])
    return sc, run(sc, ScriptedDiver(depth, descent_mps=sp, ascent_mps=sp, kick_f=f))


def dyn_dive(arch, dist, seed=3, **kw):
    sc = Scenario(seed=seed, archetype=arch, discipline="DYN", announced_distance_m=dist, lead_kg=0.0, max_time_s=900.0)
    return sc, run(sc, DynDiver(dist, **kw))


@pytest.mark.parametrize("disc", ["FIM", "CNF"])
def test_stroke_optimum_is_per_discipline(disc):
    f_opt, w, scale = M.STROKES[disc]
    fs = [i / 100 for i in range(5, 200)]
    best = max(fs, key=lambda f: M.kick_thrust(100.0, f, 1.0, 0.0, M.STROKES[disc]) / f)       # efficiency-like: thrust per Hz
    assert M.kick_effectiveness(f_opt, f_opt, w) == pytest.approx(1.0)
    assert M.kick_effectiveness(4 * f_opt, f_opt, w) < 0.01          # mashing does nothing for any discipline
    assert M.STROKES["CNF"][2] < M.STROKES["FIM"][2] < M.STROKES["CWT"][2]
    assert best > 0


@pytest.mark.parametrize("disc", ["FIM", "CNF"])
def test_arm_disciplines_are_slower_and_shallower_than_fins(disc):
    sc, d = line_dive(disc, "trained", 20)
    assert d.outcome == "success"
    cwt = run(Scenario(seed=3, archetype="trained", announced_depth_m=20), ScriptedDiver(20))
    assert d.t > cwt.t                                               # no fins: a longer dive for the same depth


def test_reach_ordering_novice_trained_elite():
    """The same depth is harder for the weaker archetype, and CNF is harder than FIM."""
    ok = lambda disc, arch, depth: line_dive(disc, arch, depth)[1].outcome == "success"
    assert ok("FIM", "novice", 10) and ok("FIM", "trained", 30) and ok("FIM", "elite", 40)
    assert ok("CNF", "elite", 30) and not ok("CNF", "trained", 30)
    assert not ok("CNF", "novice", 30)


def test_dyn_distance_and_walls():
    sc, d = dyn_dive("trained", 100)
    assert d.outcome == "success" and d.dist == pytest.approx(100.0, abs=3.0)
    assert 0.0 <= d.x <= sc.pool_m                                   # never leaves the pool
    assert d.score == pytest.approx(d.dist, abs=0.5) and d.score >= 100


def test_dyn_turns_only_at_walls():
    sc = Scenario(seed=1, discipline="DYN", lead_kg=0.0)
    from depthcharge.dive import Dive
    d = Dive(sc)
    d.step({"dir": -1, "f": 0.8, "a": 0.5})                          # mid-pool turn request is ignored
    for _ in range(200):
        d.step()
    assert d.dir == 1 and d.x > 0


def test_dyn_short_and_protocol_failures():
    sc = Scenario(seed=2, discipline="DYN", announced_distance_m=100.0, lead_kg=0.0, max_time_s=600.0)
    d = run(sc, DynDiver(30.0))                                      # finishes at 30 m after announcing 100 m
    assert d.outcome == "short"
    d2 = run(sc, DynDiver(100.0, protocol_delay_s=40.0))             # too slow with the surface protocol
    assert d2.outcome == "protocol_failed"


def test_dyn_blackout_beyond_limits():
    _, d = dyn_dive("novice", 250)
    assert d.outcome == "blackout"
    _, e = dyn_dive("elite", 250)
    assert e.outcome == "success"                                    # the elite archetype can


def test_dyn_hypoxic_samba_penalises_score():
    _, d = dyn_dive("trained", 200, extra_m=0.0)
    assert d.outcome == "success" and d.samba and d.score == pytest.approx(d.dist - 10.0, abs=0.5)


@pytest.mark.parametrize("disc", ["FIM", "CNF", "DYN"])
def test_replay_is_deterministic_for_each_discipline(disc):
    rng = random.Random(11)
    for _ in range(12):
        arch = rng.choice(["novice", "trained", "elite"])
        seed = rng.randrange(1, 10_000)
        if disc == "DYN":
            sc, d = dyn_dive(arch, rng.choice([50, 75, 100, 150]), seed=seed)
        else:
            sc, d = line_dive(disc, arch, rng.choice([10, 15, 20, 25]), seed=seed)
        assert replay(sc, d.log).digest() == d.digest()
        assert verify(sc, d.log, d.digest())
        tampered = [[t, dict(c)] for t, c in d.log]
        for _, c in tampered:
            if "a" in c:
                c["a"] = 1.0
                break
        if tampered != d.log:
            assert not verify(sc, tampered, d.digest())


def test_discipline_validation():
    assert set(DISCIPLINES) == {"CWT", "FIM", "CNF", "DYN", "STA"}
    for bad in (dict(discipline="XYZ"), dict(discipline="DYN", announced_distance_m=5), dict(discipline="DYN", pool_m=500)):
        with pytest.raises(ValueError):
            Scenario(**bad).validate()


def _post(app, path, body):
    status, payload, _ = app.handle("POST", path, body)
    assert status == 200, payload
    return payload


def test_client_api_plays_a_dynamic_swim_with_coarse_controls():
    """A proxy player using only what the page sends (f, a, dir, finish and protocol pulses) completes a 50 m swim."""
    from depthcharge.play.server import App
    app = App()
    st = _post(app, "/api/new", {"discipline": "DYN", "distance": 50, "lead": 0, "archetype": "trained", "seed": 4})
    assert st["scenario"]["discipline"] == "DYN" and st["ghost"] and st["coach"]["title"]
    f = st["scenario"]["stroke_f"]
    last, change = None, {"dir": 1}
    for _ in range(3000):
        o = st["observation"]
        if o["ended"]:
            break
        change = {"dir": 1, "f": f, "a": 0.5}
        if o["surfaced"]:
            change = {"f": 0.0, "a": 0.0, "breathe": True}
            step = o["protocol_next"]
            if step and o["t"] - (last if last is not None else o["t"]) >= 2.0 or (step and last is None):
                change[step] = True
                last = o["t"]
            last = o["t"] if last is None else last
        elif o["distance_m"] >= 50:
            change = {"f": 0.0, "a": 0.0, "finish": True}
        st = _post(app, "/api/step", {"n": 10, "change": change})
    assert st["observation"]["ended"] and st["debrief"]["outcome"] == "success", st.get("debrief")
    assert st["debrief"]["verified"]


def test_client_api_fim_session_has_pull_stroke_and_coach():
    from depthcharge.play.server import App
    app = App()
    st = _post(app, "/api/new", {"discipline": "FIM", "depth": 15, "lead": 2.5, "seed": 2})
    assert st["scenario"]["stroke_f"] == pytest.approx(0.35) and st["coach"] is not None and st["ghost"]
    status, payload, _ = app.handle("POST", "/api/new", {"discipline": "STA"})
    assert status == 400
