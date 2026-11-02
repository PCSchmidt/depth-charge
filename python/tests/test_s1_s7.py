"""S1 (pressure, lung volume, buoyancy) and S7 (stroke model)."""
import math

import pytest

from depthcharge import model as M
from depthcharge.dive import ARCHETYPES, C_WORK, Dive, Scenario

VL = 0.006   # 6 L of lung gas at the surface


@pytest.mark.parametrize("z", [0.0, 3.0, 10.0, 25.0, 40.0])
def test_boyle_lung_volume_matches_pressure_ratio(z):
    v = M.lung_volume(z, VL)
    assert math.isclose(v * M.pressure(z), VL * M.P0, rel_tol=1e-3)


def test_ambient_pressure_and_the_ten_metre_halving():
    assert math.isclose(M.pressure(10.0), 101_325 + 1025 * 9.80665 * 10, rel_tol=1e-12)
    assert math.isclose(M.lung_volume(10.0, VL) / VL, 0.5, abs_tol=0.01)    # "halves by about 10 m" (SPEC 3.2): 0.502 in sea water


LEADS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]


def _bisect(lead):
    lo, hi = 0.0, 200.0
    assert M.net_buoyancy_force(lo, VL, lead) > 0 > M.net_buoyancy_force(hi, VL, lead)
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if M.net_buoyancy_force(mid, VL, lead) > 0 else (lo, mid)
    return lo


@pytest.mark.parametrize("lead", LEADS)
def test_neutral_depth_closed_form_equals_the_root_of_the_force(lead):
    z = M.neutral_depth(VL, lead)
    assert z is not None and abs(z - _bisect(lead)) < 0.01


def test_more_lead_means_shallower_neutral_depth_and_too_much_lead_sinks_at_the_surface():
    zs = [M.neutral_depth(VL, w) for w in LEADS]
    assert all(a > b for a, b in zip(zs, zs[1:]))
    assert M.neutral_depth(VL, 8.0) is None


def test_free_fall_direction_and_ten_metre_default():
    sc = Scenario()
    zn = M.neutral_depth(ARCHETYPES["trained"].lung_l / 1000.0, sc.lead_kg)
    assert 9.0 < zn < 13.0                                   # SPEC walkthrough: neutral near 11 m
    below, above = Dive(sc), Dive(sc)
    below.z, above.z = zn + 3.0, zn - 3.0
    below.step()
    above.step()
    assert below.v > 0.0 > above.v                           # deeper than neutral: sinks; shallower: rises


def test_kick_effectiveness_peaks_at_the_optimum_frequency():
    fs = [0.05 * i for i in range(1, 33)]
    best = max(fs, key=M.kick_effectiveness)
    assert abs(best - M.F_OPT) < 0.06 and M.kick_effectiveness(0.0) == 0.0


def _speed(f, a, arch="trained"):
    """Steady speed on the level where thrust equals drag."""
    t = M.kick_thrust(ARCHETYPES[arch].thrust_max_n, f, a, 0.0)
    return math.sqrt(t / (0.5 * M.RHO_SEA * M.CDA_STREAMLINED))


def test_s7_speed_per_oxygen_has_an_interior_optimum_and_mashing_does_not_pay():
    a = 0.6
    fs = [0.1 * i for i in range(2, 17)]
    basal = ARCHETYPES["trained"].basal_ml_min
    per_o2 = {f: _speed(f, a) / (basal + C_WORK * (a * f) ** 2) for f in fs}
    best = max(per_o2, key=per_o2.get)
    assert fs[0] < best < fs[-1]
    assert _speed(1.6, 1.0) < _speed(0.8, 1.0)                          # kicking twice as fast is slower ...
    assert C_WORK * (1.6) ** 2 > 3.9 * C_WORK * 0.8 ** 2                 # ... and costs four times the oxygen
