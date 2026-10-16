"""
Launch-event emission model -- hydrogen (LH2) engines (GWP100).

Repurposed from launch_phase_GWP100_methane_and_kersene.py for the LH2 fleet.
Same model framework (CFs, post-combustion chemistry, altitude split),
new fuel: LOX/LH2 with the Prometheus-H GG engine (and SLME for the VTHL fleet).

Key difference vs methane/kerosene:
  - BC, CH4, CO, CO2 all = 0  -> the stratospheric black-carbon penalty vanishes.
  - H2O dominates (928.4 g/kg + post-combusted unburnt H2 -> ~1.0 kg H2O/kg prop).
  - H2O high-altitude CF = 1.48e3 (instantaneous), scaled by H2O_STRATO_ADJUST
    = 0.79 -> 1.169e3 (see comment at the CF block). The launch GWP is
    H2O-dominated, so the H2O CF and its stratospheric-adjustment factor
    are the MAIN terms (and main uncertainty) of the result.

Reference: Dominguez Calabuig et al., "Environmental life cycle assessment of
reusable launch vehicle fleets", Acta Astronautica 221 (2024).
  - Table 2 : CFs (aviation vs high-altitude)
  - Table 4 : emission indices (Prometheus-H, Prometheus-M, SLME)
  - Section 3.6 : altitude split 58.9% strato / 41.1% tropo; survival 75.4% / 4.0%.
"""

import json
from pathlib import Path
script_dir = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# 1. CHARACTERIZATION FACTORS  (GWP100, kg CO2eq per kg emitted) -- Table 2
# ----------------------------------------------------------------------
CF_AV = {   # aviation (tropospheric) CFs
    "BC": 1166.0,
    "CH4": 29.8,
    "CO": 4.0,
    "H2": 12.8,
    "CO2": 1.00,
    "H2O": 0.06,
    "NOx": 114.0,
    "OHx": 0.0,
}

# ---------------------------------------------------------------------------
# H2O stratospheric-adjustment factor.
#
# The instantaneous high-altitude H2O CF of 1.48e3 kg CO2eq/kg (Miraux [29],
# after Ross & Sheaffer [2]) is scaled to the "relaxed radiative forcing after
# stratospheric adjustment", as recommended in Dominguez Calabuig et al. (2024),
# Sec. 4.4.
#
# The factor 0.79 (a ~21% reduction) is ASSUMED, not derived. It is broadly
# consistent with the ~10-20% reduction from stratospheric adjustment typical
# of greenhouse-gas forcings (Myhre et al. 2013, IPCC AR5 Ch. 8; Hansen et al.
# 2005), and is chosen so that the H2O-dominated hydrogen fleet reproduces the
# paper's Table 6 CC* (159.673 Tg) -- a consistency choice, NOT an independent
# validation.
#
# Caveat: Pletzer et al. (2022) [60] report a stratosphere-adjusted H2O forcing
# of 0.39-0.43 mW/(m2 Tg), which would imply a substantially LARGER reduction
# than 0.79. The present factor is therefore a conservative (upper-bound)
# adjustment, and the H2O term should be treated as highly uncertain.
# ---------------------------------------------------------------------------
H2O_STRATO_ADJUST = 0.79
CF_HIGH = {  # high-altitude (stratospheric) CFs
    "BC": 1.60e6,
    "CH4": 29.8,
    "CO": 4.0,
    "H2": 12.8,
    "CO2": 1.31,
    "H2O": 1.48e3 * H2O_STRATO_ADJUST,   # = 1.169e3 (relaxed / stratosphere-adjusted)
    "NOx": 0,
    "OHx": 0.0,
}

CF_AL2O3_HIGH = 2.79e5   # reentry demise only, not launch exhaust

# ----------------------------------------------------------------------
# 2. EMISSION INDICES  (frozen, nozzle-exit, g per kg propellant) -- Table 4
# ----------------------------------------------------------------------
EI_H2 = {   # Prometheus-H GG (LH2 VTVL fleet)
    "BC": 0.0,
    "CH4": 0.0,
    "CO": 0.0,
    "H2": 47.706,
    "CO2": 0.0,
    "H2O": 928.4,
    "NOx": 1.0,
    "OHx": 19.160,
}

EI_SLME = {  # SLME staged-combustion (RLVC4 VTHL fleet)
    "BC": 0.0,
    "CH4": 0.0,
    "CO": 0.0,
    "H2": 24.133,
    "CO2": 0.0,
    "H2O": 975.8,
    "NOx": 1.0,
    "OHx": 0.018,
}

SPECIES = ["BC", "CH4", "CO", "H2", "CO2", "H2O", "NOx", "OHx"]

# Post-combustion stoichiometry: burned combustible -> CO2 / H2O
BURNS_TO = {
    "BC": [("CO2", 44.0 / 12.0)],
    "CO": [("CO2", 44.0 / 28.0)],
    "CH4": [("CO2", 44.0 / 16.0), ("H2O", 36.0 / 16.0)],
    "H2": [("H2O", 18.0 / 2.0)],   # unburnt H2 -> 9x its mass in H2O
}

COMBUSTIBLES = {"BC", "CO", "CH4", "H2"}

FRAC_STRATO = 0.589
FRAC_TROPO = 1.0 - FRAC_STRATO
SURV_STRATO = 0.754
SURV_TROPO = 0.04


def post_plume(ei):
    """Effective emission factors (g pollutant / kg propellant BURNED IN THE LAYER)."""
    tropo, strato = {}, {}
    for sp in SPECIES:
        if sp in COMBUSTIBLES:
            tropo[sp] = ei[sp] * SURV_TROPO
            strato[sp] = ei[sp] * SURV_STRATO
        else:
            tropo[sp] = ei[sp]
            strato[sp] = ei[sp]
    for sp in COMBUSTIBLES:
        burned_tropo = ei[sp] * (1.0 - SURV_TROPO)
        burned_strato = ei[sp] * (1.0 - SURV_STRATO)
        for product, ratio in BURNS_TO[sp]:
            tropo[product] = tropo.get(product, 0.0) + burned_tropo * ratio
            strato[product] = strato.get(product, 0.0) + burned_strato * ratio
    return tropo, strato



def gwp(ei):
    """Return (gwp_av, gwp_high): per-species GWP100 [g CO2eq/kg propellant]."""
    tropo, strato = post_plume(ei)
    out_av, out_high = {}, {}
    for sp in SPECIES:
        out_av[sp] = (FRAC_TROPO * tropo[sp] * CF_AV[sp]
                      + FRAC_STRATO * strato[sp] * CF_AV[sp])
        out_high[sp] = (FRAC_TROPO * tropo[sp] * CF_AV[sp]
                        + FRAC_STRATO * strato[sp] * CF_HIGH[sp])
    return out_av, out_high


# ----------------------------------------------------------------------
# OUTPUT
# ----------------------------------------------------------------------
ENGINES = [("Prometheus-H", EI_H2), ("SLME", EI_SLME)]


def print_cf_table():
    print("=== TABLE 1 - Characterization factors (GWP100, kg CO2eq/kg) ===")
    print(f"{'Species':<8}{'CF aviation':>14}{'CF high-alt.':>16}")
    print("-" * 40)
    for sp in SPECIES:
        print(f"{sp:<8}{CF_AV[sp]:>14.3f}{CF_HIGH[sp]:>16.4g}")
    print(f"{'Al2O3':<8}{'--':>14}{CF_AL2O3_HIGH:>16.3g}   (reentry demise only)")
    print()


def print_ei_table():
    print("=== TABLE 2 - Emission indices (frozen, nozzle-exit, g/kg) ===")
    print(f"{'Species':<8}{'EI Prometheus-H':>16}{'EI SLME':>14}")
    print("-" * 40)
    for sp in SPECIES:
        print(f"{sp:<8}{EI_H2[sp]:>16.3f}{EI_SLME[sp]:>14.3f}")
    print()


def print_ef_table(name, ei):
    tropo, strato = post_plume(ei)
    print(f"=== TABLE 3 - Effective emission factors, {name}  [g/kg burned in layer] ===")
    print(f"{'Species':<8}{'EF troposphere':>18}{'EF stratosphere':>18}")
    print("-" * 46)
    for sp in SPECIES:
        print(f"{sp:<8}{tropo[sp]:>18.3f}{strato[sp]:>18.3f}")
    print("  (no altitude fraction; 41.1% / 58.9% applied at GWP summation)\n")


def print_gwp_table(name, ei):
    gav, ghi = gwp(ei)
    tot_av = sum(gav.values())
    tot_hi = sum(ghi.values())
    print(f"=== TABLE 4 - GWP100, {name}  [g CO2eq/kg propellant] ===")
    print(f"{'Species':<8}{'GWP av-only':>16}{'share':>9}{'GWP av+high':>18}{'share':>9}")
    print("-" * 62)
    for sp in SPECIES:
        print(f"{sp:<8}{gav[sp]:>16,.1f}{gav[sp]/tot_av:>8.2%}"
              f"{ghi[sp]:>18,.1f}{ghi[sp]/tot_hi:>8.2%}")
    print("-" * 62)
    print(f"{'TOTAL':<8}{tot_av:>16,.1f}{'100%':>9}{tot_hi:>18,.1f}{'100%':>9}")
    print(f"  aviation-only total = {tot_av/1000:.3f} kg/kg | "
          f"av+high total = {tot_hi/1000:.1f} kg/kg | "
          f"ratio = {tot_hi/tot_av:.0f}x\n")


def save_json():
    eff, gwp_out = {}, {}
    for name, ei in ENGINES:
        tropo, strato = post_plume(ei)
        gav, ghi = gwp(ei)
        eff[name] = {
            "aviation": {sp: round(tropo[sp], 4) for sp in SPECIES},
            "high_altitude": {sp: round(strato[sp], 4) for sp in SPECIES},
        }
        gwp_out[name] = {
            "total_aviation_kg_per_kg": round(sum(gav.values()) / 1000.0, 4),
            "total_high_altitude_kg_per_kg": round(sum(ghi.values()) / 1000.0, 3),
            "aviation": {sp: round(gav[sp], 2) for sp in SPECIES},
            "high_altitude": {sp: round(ghi[sp], 2) for sp in SPECIES},
        }

    with open(script_dir/"effective_emission_indices_hydrogen.json", "w") as f:
        json.dump({
            "note": ("Effective emission indices after post-combustion, g pollutant "
                     "per kg propellant burned in the layer. 'aviation' = tropospheric "
                     "layer (4% survival); 'high_altitude' = stratospheric layer "
                     "(75.4% survival). No altitude burn fraction applied."),
            **eff,
        }, f, indent=2)

    with open(script_dir/"launch_gwp100_species_hydrogen.json", "w") as f:
        json.dump({
            "note": ("Launch-phase GWP100 per species, g CO2eq per kg propellant. "
                     "'aviation' = both bands x aviation CF; 'high_altitude' = "
                     "troposphere x aviation CF + stratosphere x high-alt CF. "
                     "Altitude burn fractions (41.1% / 58.9%) applied."),
            **gwp_out,
        }, f, indent=2)

    print("Saved: effective_emission_indices_hydrogen.json, launch_gwp100_species_hydrogen.json")


# ----------------------------------------------------------------------
# Bonus sanity check: per-launch launch-phase GWP for the LH2 VTVL fleet.
# Propellant masses (Mg): L-RLV = 240 + 61; XXL = 3*240 + 61 (both variants).
# ----------------------------------------------------------------------
LAUNCHERS = {
    "L-RLV: H240+H61":        240 + 61,
    "XXL-RLV: 2H240+H240+H61": 3 * 240 + 61,
    "XXL-RLV exp. core":      3 * 240 + 61,
}


def print_per_launch():
    gav, ghi = gwp(EI_H2)
    print("=== PER-LAUNCH launch-phase GWP100, hydrogen fleet (Prometheus-H) ===")
    print(f"{'Launcher':<24}{'mp [Mg]':>10}{'GWP av [Gg]':>14}{'GWP high [Gg]':>16}")
    print("-" * 64)
    for la, mp in LAUNCHERS.items():
        print(f"{la:<24}{mp:>10.0f}{mp * sum(gav.values()) / 1e6:>14.4f}"
              f"{mp * sum(ghi.values()) / 1e6:>16.2f}")
    print("  (launch phase only; aviation-CF share of Table-5 totals is ~3%, see all-phases step)\n")


if __name__ == "__main__":
    print_cf_table()
    print_ei_table()
    print_ef_table("hydrogen (Prometheus-H)", EI_H2)
    print_ef_table("hydrogen (SLME)", EI_SLME)
    print_gwp_table("hydrogen (Prometheus-H)", EI_H2)
    print_gwp_table("hydrogen (SLME)", EI_SLME)
    print_per_launch()
    save_json()
