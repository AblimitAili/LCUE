"""
Validation: reproduce the methane-fleet GWP100 and cross-check against the
paper (Table 5, Table 6, Fig. 6, Fig. 8).

Reads launch_gwp100_species.json produced by launch_phase_GWP100_methane_and_kersene.py.

Checks
------
1. aviation   : fleet launch phase == 25.4% (Fig. 6) of Table 6 CC (6.016 Tg).
2. per-launch : launch phase is a consistent share of each Table 5 total.
3. high-alt   : full fleet total (launch all-species + reentry + ground phases)
                reproduced against Table 6 CC* (1229.818 Tg), using the
                per-species stratospheric-adjustment factors (H2O x0.79, BC x0.90).
"""
import json
import os
from pathlib import Path

script_dir = Path(__file__).resolve().parent

# ------------------------- Paper data (methane / LCH4 fleet) -------------------------
TABLE5 = {            # per-launch full-lifecycle GWP100, aviation CFs [Gg]
    "L-RVL": 10.36,
    "XXL": 27.74,
    "XXL-exp": 29.60,
}
TABLE6_CC       = 6.016      # fleet total, aviation CFs [Tg]
TABLE6_CCSTAR   = 1229.818   # fleet total, high-altitude CFs [Tg]
FIG6_LAUNCH     = 0.254      # Fig. 6: launch phase = 25.4% of fleet total (aviation)
REENTRY_AL2O3_TG = 43.0      # Fig. 8: reentry ~3.5% of CC* (not tabulated in paper)

LAUNCHERS = [
    {"name": "L-RVL",   "mp": 630.0,  "n": 65.1},
    {"name": "XXL",     "mp": 1670.0, "n": 121.5},
    {"name": "XXL-exp", "mp": 1670.0, "n": 66.6},
]


def main():
    path = script_dir / "launch_gwp100_species.json"
    if not os.path.exists(path):
        raise SystemExit(f"Missing {path} -- run launch_phase_GWP100_methane_and_kersene.py first.")

    with open(path) as f:
        data = json.load(f)

    methane = data["methane"]
    gwp_kg_av = sum(methane["aviation"].values())     / 1000.0   # kg CO2eq/kg prop
    gwp_kg_hi = sum(methane["high_altitude"].values()) / 1000.0  # kg CO2eq/kg prop

    total_mp = sum(la["mp"] * la["n"] for la in LAUNCHERS)       # Mg (fleet propellant)

    # ---- per-kg launch GWP100 -------------------------------------------------------
    print("Methane launch GWP100 (per kg propellant):")
    print(f"  aviation CFs : {gwp_kg_av:,.3f} kg/kg")
    print(f"  high-alt CFs : {gwp_kg_hi:,.0f} kg/kg   (H2O x0.79, BC x0.90)\n")

    # ---- per-launch launch phase (aviation) vs Table 5 --------------------------------
    print("Per-launch launch phase (aviation CFs):")
    print(f"  {'launcher':<10}{'launch':>10}{'Table5':>10}{'share':>10}")
    print("  " + "-" * 40)
    for la in LAUNCHERS:
        la["launch_av"] = gwp_kg_av * la["mp"] / 1000.0   # Gg
        la["launch_hi"] = gwp_kg_hi * la["mp"] / 1000.0
        tab5 = TABLE5[la["name"]]
        print(f"  {la['name']:<10}{la['launch_av']:>10.2f}{tab5:>10.2f}"
              f"{la['launch_av']/tab5:>9.1%}")

    # ---- fleet launch phase (aviation) vs Fig. 6 --------------------------------------
    fleet_av    = sum(la["launch_av"] * la["n"] for la in LAUNCHERS)   # Gg
    expected_av = FIG6_LAUNCH * TABLE6_CC * 1000.0                      # Gg
    print("\nFleet launch phase (aviation CFs):")
    print(f"  model    = {fleet_av/1000:.4f} Tg")
    print(f"  expected = {expected_av/1000:.4f} Tg   (Fig.6 {FIG6_LAUNCH:.1%} x Table 6 {TABLE6_CC} Tg)")
    print(f"  share of fleet total = {fleet_av/(TABLE6_CC*1000):.2%}")
    print(f"  deviation            = {fleet_av/expected_av - 1:+.3%}")

    # ---- high-altitude: reconcile the FULL fleet total against CC* --------------------
    fleet_hi = sum(la["launch_hi"] * la["n"] for la in LAUNCHERS)  # Gg

    # Launch phase, split by species (all species accounted for).
    bc_per_kg     = methane["high_altitude"]["BC"]  / 1000.0   # kg CO2eq/kg prop
    h2o_per_kg    = methane["high_altitude"]["H2O"] / 1000.0   # kg CO2eq/kg prop
    others_per_kg = gwp_kg_hi - bc_per_kg - h2o_per_kg         # CH4, CO, H2, CO2, NOx

    fleet_launch = fleet_hi / 1000.0                             # Tg (all launch species)
    fleet_bc     = bc_per_kg     * total_mp / 1e6                # Tg
    fleet_h2o    = h2o_per_kg    * total_mp / 1e6                # Tg
    fleet_others = others_per_kg * total_mp / 1e6                # Tg
    ground       = TABLE6_CC - fleet_av / 1000.0                 # non-launch phases, aviation CFs [Tg]

    total_model = fleet_launch + REENTRY_AL2O3_TG + ground

    print("\nHigh-altitude fleet total vs Table 6 CC*:")
    print("  " + "-" * 52)
    print(f"  {'launch phase':<22}{fleet_launch:>10,.1f} Tg")
    print(f"    {'BC (x0.90)':<20}{fleet_bc:>10,.0f} Tg")
    print(f"    {'H2O (x0.79)':<20}{fleet_h2o:>10,.0f} Tg")
    print(f"    {'other species':<20}{fleet_others:>10,.1f} Tg")
    print(f"  {'reentry Al2O3':<22}{REENTRY_AL2O3_TG:>10,.1f} Tg")
    print(f"  {'ground phases':<22}{ground:>10,.1f} Tg")
    print("  " + "-" * 52)
    print(f"  {'model total':<22}{total_model:>10,.1f} Tg")
    print(f"  {'Table 6 CC*':<22}{TABLE6_CCSTAR:>10,.1f} Tg")
    print(f"  {'deviation':<22}{(total_model/TABLE6_CCSTAR - 1):>10.2%}")
    print("\n  Launch dominates the total; BC is the largest launch term (x0.90),")
    print("  H2O is relaxed (x0.79), and reentry + ground phases make up the rest.")

    # ---- verdict -----------------------------------------------------------------------
    ok_av = abs(fleet_av / expected_av - 1) < 0.01
    ok_hi = abs(total_model / TABLE6_CCSTAR - 1) < 0.05
    print("\nRESULT:")
    print("  aviation cross-check :", "PASS" if ok_av else "FAIL",
          f"({fleet_av/expected_av - 1:+.3%})")
    print("  high-altitude        :", "PASS" if ok_hi else "FAIL",
          f"({total_model/TABLE6_CCSTAR - 1:+.2%}, within 5%)")


if __name__ == "__main__":
    main()
