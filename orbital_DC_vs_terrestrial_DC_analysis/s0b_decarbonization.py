"""
s0b - Decarbonization mapping (Path 2).

For a decarbonization fraction D applied to every life-cycle phase EXCEPT
Launch and Reentry (the in-flight emissions), compute the equivalent *average*
decarbonization across all phases:

    delta = D * ground_share,   ground_share = (total - Launch - Reentry) / total

Reads the hydrogen all-phases aviation JSON (phase breakdown) only.
Run standalone to inspect the D -> delta mapping, or before s1 to document the
"average decarbonization" numbers used by the `h2_xxlrlv_exp_decarb` scenario.
"""

import json
from pathlib import Path

FLIGHT_PHASES = {"Launch", "Reentry"}

_SCRIPT_DIR = Path(__file__).resolve().parent
HYDROGEN_DIR = _SCRIPT_DIR.parent / "hydrogen_launcher_lifecycle_GWP100_analysis"
HYDROGEN_JSON = HYDROGEN_DIR / "phases_gwp100_hydrogen_launchers_aviation.json"

# Decarbonization of the non-flight phases. Keep in sync with the
# `ground_decarb` value of `h2_xxlrlv_exp_decarb` in s0_scenarios.py.
GROUND_DECARB = 0.65

DECARB_LAUNCHER = "XXL-RLV exp. core"


def load_phase_breakdown(launcher=DECARB_LAUNCHER, json_file=HYDROGEN_JSON):
    """Return {phase: Gg} for one hydrogen launcher."""
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
    return data["per_launcher_phase_Gg"][launcher]


def ground_share(phases):
    """Fraction of the launch GWP held by decarbonizable (non-flight) phases."""
    total = sum(phases.values())
    ground = sum(v for k, v in phases.items() if k not in FLIGHT_PHASES)
    return ground / total


def average_decarbonization(phases, D):
    """delta: equivalent decarbonization averaged over ALL phases."""
    return D * ground_share(phases)


def decarbonized_total(phases, D):
    """New per-launch GWP [Gg] after decarbonizing ground phases by D."""
    total = sum(phases.values())
    ground = sum(v for k, v in phases.items() if k not in FLIGHT_PHASES)
    return total - D * ground


def main():
    print("Phase breakdown (aviation CFs), hydrogen launchers:")
    for launcher in ["L-RLV", "XXL-RLV", "XXL-RLV exp. core"]:
        phases = load_phase_breakdown(launcher)
        total = sum(phases.values())
        gs = ground_share(phases)
        print(f"  {launcher:<18} ground share {gs * 100:5.1f}%   "
              f"total {total:7.3f} Gg")

    phases = load_phase_breakdown(DECARB_LAUNCHER)
    total = sum(phases.values())
    gs = ground_share(phases)
    ground = sum(v for k, v in phases.items() if k not in FLIGHT_PHASES)
    flight = total - ground
    print(f"\nDecarb launcher = {DECARB_LAUNCHER}")
    print(f"  total {total:.3f} Gg | ground {ground:.3f} Gg "
          f"({gs * 100:.1f}%) | flight {flight:.3f} Gg ({(1 - gs) * 100:.1f}%)")

    print("\nMapping  D (ground) -> delta (average) -> new total (Gg):")
    for D in [0.0, 0.25, 0.5, 0.65, 0.75, 1.0]:
        d = average_decarbonization(phases, D)
        new = decarbonized_total(phases, D)
        print(f"  {D * 100:>5.0f}%  ->  {d * 100:>5.1f}%  ->  {new:>7.3f}")

    out = {
        "launcher": DECARB_LAUNCHER,
        "ground_share": round(gs, 4),
        "flight_share": round(1 - gs, 4),
        "D": GROUND_DECARB,
        "average_decarbonization": round(average_decarbonization(phases, GROUND_DECARB), 4),
        "decarbonized_total_Gg": round(decarbonized_total(phases, GROUND_DECARB), 4),
        "original_total_Gg": round(total, 4),
    }
    with open(_SCRIPT_DIR / "decarbonization_hydrogen.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote decarbonization_hydrogen.json (D = {GROUND_DECARB}).")


if __name__ == "__main__":
    main()
