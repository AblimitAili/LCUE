"""
Scenario configuration for the orbital data centre launch (transportation) analysis.

`emission_per_launch_kg` is NOT hardcoded: it is read at import time from the
upstream all-phases GWP100 JSONs (aviation CFs) in the two LCA folders, and
converted Gg -> kg. Each scenario only says WHICH file + key to read (plus an
optional `emission_scale` for derived scenarios such as the decarbonised one).

`payload_kg` is a primary input (Wilken 2024, Table 3) and therefore stays in
the config.
"""

import json
from pathlib import Path


# ---- locations of the upstream LCA outputs (siblings of this folder) ---------
# Assumes the three analysis folders share one parent. Adjust the names here if
# your actual folder names differ.
_SCRIPT_DIR = Path(__file__).resolve().parent
HYDROCARBON_DIR = _SCRIPT_DIR.parent / "hydrocarbon_launcher_lifecycle_GWP100_analysis"
HYDROGEN_DIR    = _SCRIPT_DIR.parent / "hydrogen_launcher_lifecycle_GWP100_analysis"


def _load_launch_gwp_kg(json_file, key):
    """Read a per-launch GWP100 [Gg] from an upstream LCA JSON -> [kg].

    key:  str    -> top-level field, e.g. "total_per_launch_Gg"
          tuple  -> nested path,    e.g. ("per_launcher_sum_Gg", "L-RLV")
    """
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    for part in (key,) if isinstance(key, str) else key:
        data = data[part]
    return data * 1e6   # Gg -> kg


# Phases excluded from decarbonization: in-flight emissions cannot be "decarbonized".
FLIGHT_PHASES = {"Launch", "Reentry"}


def _load_phase_gwp_Gg(json_file, launcher):
    """Read the per-phase launch GWP100 [Gg] for one launcher."""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["per_launcher_phase_Gg"][launcher]


def _decarbonized_total_Gg(phases, ground_decarb):
    """New total [Gg] after decarbonizing every phase except Launch/Reentry.

    ground_decarb = D: fraction of the ground (non-flight) phases removed.
    """
    total = sum(phases.values())
    ground = sum(v for k, v in phases.items() if k not in FLIGHT_PHASES)
    return total - ground_decarb * ground


SCENARIOS = [
    {
        "name": "falcon9",
        "label": "Orbital DC: Falcon 9 launcher",
        "launch_json": HYDROCARBON_DIR / "falcon9_phase_gwp100_aviation.json",
        "launch_key": "total_per_launch_Gg",
        "payload_kg": 22800.0,
        "color": "black",
        "enabled": True,
    },
    {
        "name": "xxl_exp",
        "label": "Orbital DC (LCH₄ launcher)",
        "launch_json": HYDROCARBON_DIR / "phases_gwp100_methane_launchers_aviation.json",
        "launch_key": ("per_launcher_sum_Gg", "XXL-exp"),
        "payload_kg": 18900.0,
        "color": "blue",
        "enabled": False,
    },
    {
        "name": "falcon9_decarb",
        "label": "Orbital DC (Falcon 9 decarbonized 65%)",
        "launch_json": HYDROCARBON_DIR / "falcon9_phase_gwp100_aviation.json",
        "launch_key": "total_per_launch_Gg",
        "emission_scale": 0.35,          # Path 1; launcher decarbonized. 
        "payload_kg": 22800.0,
        "color": "purple",
        "enabled": False,
    },
    {
        "name": "h2_xxlrlv_exp",
        "label": "Orbital DC (LH2 XXL-RLV exp. core launcher)",
        "launch_json": HYDROGEN_DIR / "phases_gwp100_hydrogen_launchers_aviation.json",
        "launch_key": ("per_launcher_sum_Gg", "XXL-RLV exp. core"),
        "payload_kg": 19700.0,
        "color": "brown",
        "enabled": False,
    },
    {
        "name": "h2_xxlrlv_exp_decarb",
        "label": "Orbital DC: decarbonised launcher",
        "launch_json": HYDROGEN_DIR / "phases_gwp100_hydrogen_launchers_aviation.json",
        "launch_key": "XXL-RLV exp. core",
        "ground_decarb": 0.72,         # Path 1; decarbonize all-but-launch/reentry by 75%
        "payload_kg": 19700.0,
        "color": "green",
        "enabled": True,
    }
]

# ---- resolve emission_per_launch_kg from the JSONs (no hardcoding) -----------
for _sc in SCENARIOS:
    if "ground_decarb" in _sc:
        # Path 2: decarbonize every phase except Launch/Reentry by ground_decarb.
        _phases = _load_phase_gwp_Gg(_sc.pop("launch_json"), _sc.pop("launch_key"))
        _total_Gg = _decarbonized_total_Gg(_phases, _sc.pop("ground_decarb"))
        _sc["emission_per_launch_kg"] = _total_Gg * 1e6   # Gg -> kg
    else:
        _sc["emission_per_launch_kg"] = (
            _load_launch_gwp_kg(_sc.pop("launch_json"), _sc.pop("launch_key"))
            * _sc.pop("emission_scale", 1.0)
        )
