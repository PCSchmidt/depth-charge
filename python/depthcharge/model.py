"""Pressure, lung volume and buoyancy (SPEC 3.2) and the stroke model (SPEC 3.1). Pure functions, SI units.

Depth z is metres below the surface, positive down. Every number marked 'design value' is tunable for gameplay and is
not a claim about human physiology.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

P0 = 101_325.0          # Pa, surface pressure
G = 9.80665             # m/s^2
RHO_SEA = 1025.0        # kg/m^3 (fresh water: 1000)

# Diver and gear (design values)
BODY_MASS = 75.0            # kg, tissue (lungs excluded; air has no mass here)
BODY_DENSITY = 1070.0       # kg/m^3 tissue density without lung air
SUIT_MASS = 2.5             # kg
SUIT_VOLUME0 = 0.0060       # m^3 at the surface
SUIT_RESIDUAL = 0.25        # fraction of the suit volume that does not compress (neoprene cells keep some gas)

# Hydrodynamics (design values)
CDA_STREAMLINED = 0.05      # m^2, Cd*A head-first with arms extended
CDA_BROADSIDE = 0.15        # m^2, turning or unstreamlined
ADDED_MASS = 12.0           # kg of entrained water
# Stroke
F_OPT = 0.8                 # Hz, kick frequency at which the stroke is most effective
F_WIDTH = 0.35              # log-width of the effectiveness peak


def pressure(z: float, rho: float = RHO_SEA) -> float:
    """Ambient pressure in Pa at depth z (m)."""
    return P0 + rho * G * max(z, 0.0)


def lung_volume(z: float, v_surface: float, rho: float = RHO_SEA) -> float:
    """Boyle's law: lung gas volume (m^3) at depth z for v_surface of gas at the surface."""
    return v_surface * P0 / pressure(z, rho)


def suit_volume(z: float, rho: float = RHO_SEA) -> float:
    return SUIT_VOLUME0 * (SUIT_RESIDUAL + (1.0 - SUIT_RESIDUAL) * P0 / pressure(z, rho))


def displaced_volume(z: float, v_lung_surface: float, rho: float = RHO_SEA) -> float:
    return BODY_MASS / BODY_DENSITY + lung_volume(z, v_lung_surface, rho) + suit_volume(z, rho)


def net_buoyancy_force(z: float, v_lung_surface: float, lead_kg: float, rho: float = RHO_SEA) -> float:
    """Upward force in N (positive = floats up). Lead is treated as zero-volume."""
    return G * (rho * displaced_volume(z, v_lung_surface, rho) - (BODY_MASS + SUIT_MASS + lead_kg))


def neutral_depth(v_lung_surface: float, lead_kg: float, rho: float = RHO_SEA) -> float | None:
    """Closed-form depth at which net buoyancy is zero, or None if there is none at or below the surface.

    F = 0  =>  rho*(Vb + Vs0*r + u*(VL0 + Vs0*(1-r))) = M, with u = P0/P.
    """
    vb = BODY_MASS / BODY_DENSITY
    m = BODY_MASS + SUIT_MASS + lead_kg
    u = (m / rho - vb - SUIT_VOLUME0 * SUIT_RESIDUAL) / (v_lung_surface + SUIT_VOLUME0 * (1.0 - SUIT_RESIDUAL))
    if not 0.0 < u <= 1.0:
        return None
    return (P0 / u - P0) / (rho * G)


# Per-discipline stroke: (optimal frequency Hz, log-width, thrust scale). Design values: arm pulls and breaststroke are slower
# and weaker than a fin kick. CWT, DYN and STA use the fin kick.
STROKES = {"CWT": (0.8, 0.35, 1.0), "DYN": (0.8, 0.35, 1.0), "STA": (0.8, 0.35, 1.0), "FIM": (0.35, 0.35, 0.75), "CNF": (0.3, 0.35, 0.6)}


def kick_effectiveness(f: float, f_opt: float = F_OPT, width: float = F_WIDTH) -> float:
    """Log-normal peak in kick frequency: too slow does little, too fast is wasted (no button-mashing exploit)."""
    if f <= 0.0:
        return 0.0
    x = math.log(f / f_opt)
    return math.exp(-x * x / (2.0 * width * width))


def kick_thrust(t_max: float, f: float, amplitude: float, fatigue: float, stroke: tuple = STROKES["CWT"]) -> float:
    """Thrust magnitude in N."""
    f_opt, width, scale = stroke
    return t_max * scale * amplitude * (f / f_opt) * kick_effectiveness(f, f_opt, width) * (1.0 - 0.35 * fatigue)


def drag(v: float, cda: float, rho: float = RHO_SEA) -> float:
    """Drag force in N opposing velocity v (m/s)."""
    return 0.5 * rho * cda * v * abs(v)
