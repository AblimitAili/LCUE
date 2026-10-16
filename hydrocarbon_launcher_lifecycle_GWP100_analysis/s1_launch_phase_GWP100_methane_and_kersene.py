"""
Launch-event emission model — reference tables (GWP100).

Reproduces the paper's launch-event model (Section 3.6) and extends it to kerosene.

Output structure (four stages):
  1. CF reference table   : characterization factors (aviation vs high-altitude).
  2. EI reference table   : frozen (nozzle-exit) emission indices, methane vs kerosene.
  3. Effective EF table   : net emission factor per kg burned IN EACH LAYER
                            (post-combustion applied, NO altitude fraction yet).
  4. GWP100 tables        : per fuel (methane, kerosene), two CF scenarios:
       - "aviation only"          : both bands x aviation CF.
       - "aviation + high-alt."   : tropospheric band x aviation CF,
                                    stratospheric band x high-alt CF.
     The altitude burn fractions (41.1% / 58.9%) are applied HERE, at summation.

Convention (Option B):
  - Effective EF  = frozen EI x survival(layer)   ->  per kg burned in that layer
        (an intrinsic property of the layer's post-combustion chemistry).
  - Burn fraction = where the propellant burns (trajectory) -> applied only
        when summing GWP across the two layers.
  Keeping the two separate: EF = chemistry, fraction = trajectory.

Model constants (paper Section 3.6):
  - Altitude split     : 58.9% of propellant burns in the stratosphere, 41.1% troposphere.
  - Survival (combustibles BC, CO, CH4, H2 after post-combustion):
        stratosphere   75.4%
        troposphere     4.0%
  - Burned combustibles are converted to CO2 and H2O (strict mass balance).
"""

import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent

# ----------------------------------------------------------------------
# 1. CHARACTERIZATION FACTORS  (GWP100, kg CO2eq per kg emitted)
# ----------------------------------------------------------------------
CF_AV = {   # aviation (tropospheric) CFs -- Table 2
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
# Stratospheric-adjustment ("relaxation") factors for the instantaneous
# high-altitude CFs (Ross & Sheaffer [2] -> Calabuig et al. [3], Sec. 4.4:
# "this approach should be applied to the relaxed radiative forcing after
# stratospheric adjustment").
#
# Per-species factors (calibrated, not derived):
#   H2O : 1.48e3 -> 1.169e3  (x 0.79, ~21% reduction)
#   BC  : 1.60e6 -> 1.44e6   (x 0.90, ~10% reduction)
#
# Calibration targets (Calabuig et al., Table 6 CC*):
#   H2O x 0.79 -> hydrogen fleet CC* = 159.673 Tg   (H2O-dominated)
#   BC  x 0.90 -> methane  fleet CC* = 1229.818 Tg  (BC-dominated)
# H2O's larger reduction than BC's is physically plausible (stratospheric
# water vapour drives a stronger temperature response than soot). Pletzer
# et al. (2022) [60] imply an even larger H2O reduction, so 0.79 is
# conservative; no published BC factor exists, so 0.90 is a calibration.
# ---------------------------------------------------------------------------

H2O_STRATO_ADJUST = 0.79
BC_STRATO_ADJUST  = 0.90

CF_HIGH = {  # high-altitude (stratospheric) CFs -- Table 2
    "BC": 1.60e6 * BC_STRATO_ADJUST,   # = 1.44e6 (relaxed)
    "CH4": 29.8,      # no separate high-alt value -> aviation CF retained
    "CO": 4.0,        #   (well-mixed gas, no altitude dependence)
    "H2": 12.8,       #   (well-mixed gas, no altitude dependence)
    "CO2": 1.31,
    "H2O": 1.48e3 * H2O_STRATO_ADJUST,   # = 1.169e3 (relaxed)
    "NOx": 0.0,       # no high-altitude CF available (was 619.0)
    "OHx": 0.0,
}


# Al2O3 only has a high-altitude CF (reentry demise, NOT launch exhaust).
CF_AL2O3_HIGH = 2.79e5

# ----------------------------------------------------------------------
# 2. EMISSION INDICES  (frozen, nozzle-exit, g per kg propellant)
# ----------------------------------------------------------------------
EI_CH4 = {   # Prometheus-M (Table 4)
    "BC": 4.6916,
    "CH4": 54.706,
    "CO": 168.8,
    "H2": 5.4457,
    "CO2": 312.4,
    "H2O": 425.6,
    "NOx": 1.0,
    "OHx": 17.816,
}

# EI_KER = {   # Merlin 1D (user estimate)
#     "BC": 22.0,
#     "CH4": 0.0,
#     "CO": 318.0,
#     "H2": 10.0,
#     "CO2": 637.0,
#     "H2O": 340.0,
#     "NOx": 1.0,
#     "OHx": 0.0,
# }

# references page 40 of Commercial Space Vehicle Emissions Modeling for all species but BC from Falcon 9
# for bc emissions Indice, Tsigaridis et al "Composition and Climate Impacts of increasing launches to Low Earth Orbit" implys 22gg/kg by sayin
# For LNG engine, we assume vacuum 𝐸𝐼(𝐵𝐶,70𝑘𝑚) = 7.5 g/kg, one fourth of the value that is commonly assumed for kerosene engines. 
# In "The Climate and Ozone Impacts of Black Carbon Emissions From Global Rocket Launches - Supporting Informaion" Meloney et al states "rocket EI(BC) equals approximately 10 to 30 g/kg."
# and further states "For the purposes of calculating the global rocket fleet-wide soot emission we assume a stratospheric (non-afterburning) EI(BC) equal to 20 g/kg (e.g., 2% mass fraction)" 
EI_KER = {   # Merlin 1D (user estimate)
    "BC": 20.0, # range 10- 30
    "CH4": 0.0,
    "CO": 372.0,
    "H2": 12.0,
    "CO2": 352.0,
    "H2O":263.0,
    "NOx": 1.0,
    "OHx": 0.0,
}

SPECIES = ["BC", "CH4", "CO", "H2", "CO2", "H2O", "NOx", "OHx"]

# Post-combustion stoichiometry: burned combustible -> CO2 / H2O
# (a species may yield more than one product, e.g. CH4 -> CO2 + H2O)
BURNS_TO = {
    "BC": [("CO2", 44.0 / 12.0)],                        # 1 g C   -> 44/12 g CO2
    "CO": [("CO2", 44.0 / 28.0)],                        # 1 g CO  -> 44/28 g CO2
    "CH4": [("CO2", 44.0 / 16.0), ("H2O", 36.0 / 16.0)],  # 1 g CH4 -> CO2 + H2O
    "H2": [("H2O", 18.0 / 2.0)],                         # 1 g H2  -> 18/2 g H2O
}

COMBUSTIBLES = {"BC", "CO", "CH4", "H2"}

FRAC_STRATO = 0.589
FRAC_TROPO = 1.0 - FRAC_STRATO
SURV_STRATO = 0.754
SURV_TROPO = 0.04


def post_plume(ei):
    """
    Effective emission factors (g pollutant / kg propellant BURNED IN THE LAYER).
    Post-combustion is applied, but NOT the altitude burn fraction.
    Returns {"tropo": {...}, "strato": {...}}.
    """
    tropo, strato = {}, {}

    # Pass 1: base amounts for every species (survival only, no altitude fraction)
    for sp in SPECIES:
        if sp in COMBUSTIBLES:
            tropo[sp] = ei[sp] * SURV_TROPO
            strato[sp] = ei[sp] * SURV_STRATO
        else:
            tropo[sp] = ei[sp]
            strato[sp] = ei[sp]

    # Pass 2: burned combustibles -> CO2 / H2O products (added, never overwritten)
    for sp in COMBUSTIBLES:
        burned_tropo = ei[sp] * (1.0 - SURV_TROPO)
        burned_strato = ei[sp] * (1.0 - SURV_STRATO)
        for product, ratio in BURNS_TO[sp]:
            tropo[product] = tropo.get(product, 0.0) + burned_tropo * ratio
            strato[product] = strato.get(product, 0.0) + burned_strato * ratio

    return tropo, strato


def gwp(ei):
    """Return (gwp_av, gwp_high): per-species GWP100 [g CO2eq/kg propellant].

    Burn fractions are applied here, at summation:
      aviation-only  = f_tropo*EF_tropo*CF_av + f_strato*EF_strato*CF_av
      aviation+high  = f_tropo*EF_tropo*CF_av + f_strato*EF_strato*CF_high
    """
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
def print_cf_table():
    print("=== TABLE 1 — Characterization factors (GWP100, kg CO2eq/kg) ===")
    print(f"{'Species':<8}{'CF aviation':>14}{'CF high-alt.':>16}")
    print("-" * 40)
    for sp in SPECIES:
        print(f"{sp:<8}{CF_AV[sp]:>14.3f}{CF_HIGH[sp]:>16.4g}")
    print(f"{'Al2O3':<8}{'--':>14}{CF_AL2O3_HIGH:>16.3g}   (reentry demise only)")
    print()


def print_ei_table():
    print("=== TABLE 2 — Emission indices (frozen, nozzle-exit, g/kg) ===")
    print(f"{'Species':<8}{'EI methane':>14}{'EI kerosene':>14}")
    print("-" * 38)
    for sp in SPECIES:
        print(f"{sp:<8}{EI_CH4[sp]:>14.3f}{EI_KER[sp]:>14.3f}")
    print()


def print_ef_table(name, ei):
    """Effective emission factors, per kg burned in each layer (unweighted)."""
    tropo, strato = post_plume(ei)
    print(f"=== TABLE 3 — Effective emission factors, {name}  [g/kg burned in layer] ===")
    print(f"{'Species':<8}{'EF troposphere':>18}{'EF stratosphere':>18}")
    print("-" * 46)
    for sp in SPECIES:
        print(f"{sp:<8}{tropo[sp]:>18.3f}{strato[sp]:>18.3f}")
    print("  (no altitude fraction; 41.1% / 58.9% applied at GWP summation)\n")


def print_gwp_table(name, ei):
    gav, ghi = gwp(ei)
    tot_av = sum(gav.values())
    tot_hi = sum(ghi.values())
    print(f"=== TABLE 4 — GWP100, {name}  [g CO2eq/kg propellant] ===")
    print(f"{'Species':<8}{'GWP av-only':>16}{'share':>9}{'GWP av+high':>18}{'share':>9}")
    print("-" * 62)
    for sp in SPECIES:
        print(f"{sp:<8}{gav[sp]:>16,.1f}{gav[sp]/tot_av:>8.2%}"
              f"{ghi[sp]:>18,.1f}{ghi[sp]/tot_hi:>8.2%}")
    print("-" * 62)
    print(f"{'TOTAL':<8}{tot_av:>16,.1f}{'100%':>9}{tot_hi:>18,.1f}{'100%':>9}")
    print(f"  aviation-only total = {tot_av/1000:.3f} kg/kg | "
          f"av+high total = {tot_hi/1000:.1f} kg/kg | "
          f"ratio = {tot_hi/tot_av:.1f}x\n")


def save_json():
    """Save effective EIs and per-species launch GWP100 to JSON (both fuels).

    File 1 -- effective_emission_indices.json
        Effective emission indices after post-combustion, g pollutant per kg
        propellant burned IN THE LAYER (no altitude burn fraction applied).
        "aviation"     -> tropospheric layer (4% survival)
        "high_altitude"-> stratospheric layer (75.4% survival)

    File 2 -- launch_gwp100_species.json
        Launch-phase GWP100 per species, g CO2eq per kg propellant.
        "aviation"     -> both bands x aviation CF
        "high_altitude"-> troposphere x aviation CF + stratosphere x high-alt CF
        Altitude burn fractions (41.1% / 58.9%) are applied here.
    """
    # (1) Effective emission indices, per layer
    eff = {}
    for key, ei in (("methane", EI_CH4), ("kerosene", EI_KER)):
        tropo, strato = post_plume(ei)
        eff[key] = {
            "aviation": {sp: round(tropo[sp], 4) for sp in SPECIES},
            "high_altitude": {sp: round(strato[sp], 4) for sp in SPECIES},
        }
    with open(script_dir/"effective_emission_indices.json", "w") as f:
        json.dump({
            "note": ("Effective emission indices after post-combustion, g pollutant "
                     "per kg propellant burned in the layer. 'aviation' = tropospheric "
                     "layer (4% survival); 'high_altitude' = stratospheric layer "
                     "(75.4% survival). No altitude burn fraction applied."),
            **eff,
        }, f, indent=2)

    # (2) Launch-phase GWP100, per species
    g = {}
    for key, ei in (("methane", EI_CH4), ("kerosene", EI_KER)):
        gav, ghi = gwp(ei)
        g[key] = {
            "aviation": {sp: round(gav[sp], 2) for sp in SPECIES},
            "high_altitude": {sp: round(ghi[sp], 2) for sp in SPECIES},
        }

    # (3) Kerosene BC sweep (EI(BC) 10-30 g/kg) for the Falcon 9 uncertainty
    # band. Aviation and high-alt GWP100 [kg/kg] are linear in EI(BC), so
    # three points define the band; mean = 20 g/kg.
    _bc_ei, _bc_av, _bc_hi = [], [], []
    for bc in (10, 20, 30):
        _ei_bc = dict(EI_KER); _ei_bc["BC"] = float(bc)
        _gav_bc, _ghi_bc = gwp(_ei_bc)
        _bc_ei.append(bc)
        _bc_av.append(round(sum(_gav_bc.values()) / 1000.0, 3))
        _bc_hi.append(round(sum(_ghi_bc.values()) / 1000.0, 3))

    with open(script_dir/"launch_gwp100_species.json", "w") as f:
        json.dump({
            "note": ("Launch-phase GWP100 per species, g CO2eq per kg propellant. "
                     "'aviation' = both bands x aviation CF; 'high_altitude' = "
                     "troposphere x aviation CF + stratosphere x high-alt CF. "
                     "Altitude burn fractions (41.1% / 58.9%) applied."),
            **g,
            "kerosene_bc_sweep": {
                "EI_g_per_kg": _bc_ei,
                "aviation_kg_per_kg": _bc_av,
                "high_altitude_kg_per_kg": _bc_hi,
            },
        }, f, indent=2)

    print("Saved: effective_emission_indices.json, launch_gwp100_species.json")


if __name__ == "__main__":
    print_cf_table()
    print_ei_table()
    print_ef_table("methane (Prometheus-M)", EI_CH4)
    print_ef_table("kerosene (Merlin 1D)", EI_KER)
    print_gwp_table("methane (Prometheus-M)", EI_CH4)
    print_gwp_table("kerosene (Merlin 1D)", EI_KER)
    save_json()
