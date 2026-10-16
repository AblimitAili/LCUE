"""
Recover per-launch phase GWP100 for Falcon 9 (kerosene/RP-1 + LOX), Starlink.

Method (same as the methane-fleet recovery):
  each LCA phase scales with a single driver, and the per-unit coefficient is
  reused from the methane-fleet recovery -- EXCEPT the two fuel-specific phases:

    Launch       -> kerosene combustion: read from launch_gwp100_species.json
                    (aviation CFs ~13.5 kg/kg; high-alt CFs with BC x0.90 and
                    H2O x0.79 stratospheric-adjustment factors)
    Propellant   -> RP-1 + LOX production (fuel-specific mixture)

  Fuel-independent coefficients reused from the methane fleet (size-scaled):
    Production      0.1010  Gg / Mg amortised dry mass
    Recovery        0.0006  Gg / km downrange
    Maintenance     0.01124 Gg / Mg recovered dry mass
    Launch Campaign 0.0008  Gg / Mg propellant (size-scaled)
    Assembly        0.0008  Gg / Mg propellant (size-scaled)
    Reentry         0       (aviation CFs: Al2O3 has no factor)
                            -> non-zero under high-alt CFs (S2 Al2O3, estimate)

  High-altitude scenario (CC*): only Launch and Reentry change (stratospheric
  emissions); all ground-level phases keep their aviation coefficients.

Inputs (Falcon 9 / Starlink specs, user-provided) + stated assumptions.
"""

import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Falcon 9 inputs
# ---------------------------------------------------------------------------
DRY_MASS_BOOSTER = 22.0      # Mg   (user: "Dry mass 22,000 kg" -> reusable booster)
DRY_MASS_SECOND   = 4.5      # Mg   (assumed: expendable upper stage)
PROP_MASS         = 488.00   # Mg   (user: "Propellant mass 488,370 kg")
REUSES            = 10       #      (user: "10 launches")
PYA_LOAD_LEO = 22.8          # Mg
LAUNCHES          = 105       #      (user:  launches")

# Assumptions (not in the paper; stated for transparency)
O_F            = 2.35    # RP-1/LOX mass ratio (Merlin 1D)
DOWNRANGE_KM   = 650.0   # ASDS drone-ship landing, typical Starlink mission
RP1_PRODUCTION = 1.0     # kg CO2eq / kg RP-1 (well-to-loading, ~Jet A-1)
LOX_PRODUCTION = 8.1     # kg CO2eq / kg LOX  (Table 3, cradle-to-loading)

# Fixed display / output order for Table 2.
PHASE_ORDER = [
    'Production',
    'Propellant',
    'Assembly',
    'LaunchCampaign',
    'Launch',
    'Recovery',
    'Maintenance',
    'Reentry',
]

# ---------------------------------------------------------------------------
# Per-unit phase coefficients (Gg per driver unit)
# ---------------------------------------------------------------------------
# Fuel-specific
with open(script_dir / "launch_gwp100_species.json", encoding="utf-8") as f:
    _s1 = json.load(f)
_ker = _s1["kerosene"]
C_LAUNCH = sum(_ker["aviation"].values()) / 1000.0   # kg CO2eq/kg propellant (kerosene, aviation CFs)

# BC EI sweep (10-30 g/kg) for the Falcon 9 uncertainty band (aviation CFs).
# Only the Launch phase scales with the per-kg GWP; ground phases are fixed.
_BC_SWEEP = _s1.get("kerosene_bc_sweep", {})
BC_SWEEP_EI = _BC_SWEEP.get("EI_g_per_kg", [20])
BC_SWEEP_AV = _BC_SWEEP.get("aviation_kg_per_kg", [C_LAUNCH])

# Propellant mixture factor (kg CO2eq / kg propellant): RP-1 + LOX at O/F
RP1_FRAC = 1.0 / (1.0 + O_F)            # fuel mass fraction
LOX_FRAC = O_F / (1.0 + O_F)            # oxidiser mass fraction
C_PROPELLANT = RP1_FRAC * RP1_PRODUCTION + LOX_FRAC * LOX_PRODUCTION

# Fuel-independent (reused from methane-fleet recovery)
with open(script_dir/"phases_gwp100_methane_launchers_aviation.json", encoding="utf-8") as f:
    _METH = json.load(f)
_COH = _METH["coefficients_Gg_per_driver_unit"]

C_PRODUCTION  = _COH["Production"]       # Gg / Mg amortised dry mass
C_RECOVERY    = _COH["Recovery"]         # Gg / km downrange
C_MAINTENANCE = _COH["Maintenance"]      # Gg / Mg recovered dry mass
C_CAMPAIGN    = _COH["LaunchCampaign"]  # Gg / Mg propellant (size-scaled)
C_ASSEMBLY    = _COH["Assembly"]         # Gg / Mg propellant (size-scaled)

# ---------------------------------------------------------------------------
# High-altitude scenario (CC*) inputs
# ---------------------------------------------------------------------------
# Launch phase, altitude-resolved high-altitude CFs (kerosene) - READ from the
# launch model output (launch_gwp100_species.json), not hardcoded. Requires
# s1_launch_phase_GWP100_methane_and_kerosene.py to have been run first.
# The CFs there include the BC x0.90 and H2O x0.79 stratospheric-adjustment
# factors (see the high-altitude CF table of the Correction).
C_LAUNCH_HI_WITH_H2O = sum(_ker["high_altitude"].values()) / 1000.0                  # kg/kg (with H2O, relaxed)
C_LAUNCH_HI          = C_LAUNCH_HI_WITH_H2O - _ker["high_altitude"]["H2O"] / 1000.0 # kg/kg (H2O-excluded)

# BC EI sweep (10-30 g/kg) for the high-altitude band: only Launch scales.
BC_SWEEP_HI = _BC_SWEEP.get("high_altitude_kg_per_kg", [C_LAUNCH_HI_WITH_H2O])

# Reentry: F9 upper-stage (S2) demise Al2O3, high-alt CF 2.79e5 (estimate).
# Effective Al2O3 GWP per Mg dry mass calibrated from the methane fleet:
#   M110 (6.299 Mg) -> 43.04 Tg / 253.2 launches = 169.99 Gg/launch = 26.99 Gg/Mg
# Scaled by S2 dry mass (assumes similar effective Al content per kg):
REENTRY_Gg_PER_LAUNCH = 169.99 * (DRY_MASS_SECOND / 6.299)   # ~121.4 Gg


def print_phase_table(phases, title):
    """Single-launcher table: Phase | GWP100 (Gg) | Share, in PHASE_ORDER."""
    total = sum(phases.values())
    print('\n' + title)
    print('%-18s %18s %10s' % ('Phase', 'GWP100 (Gg CO2eq)', 'Share'))
    print('-' * 48)
    for ph in PHASE_ORDER:
        g = phases.get(ph, 0.0)
        pct = 100.0 * g / total if total else 0.0
        print('%-18s %18.2f %9.1f%%' % (ph, g, pct))
    print('-' * 48)
    print('%-18s %18.2f %9.1f%%' % ('Total', total, 100.0))


def reproduce_aviation():
    """Aviation-CF scenario (CC)."""
    amortised_dry = DRY_MASS_BOOSTER / REUSES + DRY_MASS_SECOND   # Mg
    recovered_dry = DRY_MASS_BOOSTER                              # Mg

    phases = {}
    phases['Production']      = C_PRODUCTION   * amortised_dry
    phases['Propellant']      = C_PROPELLANT   * PROP_MASS / 1000.0
    phases['Assembly']        = C_ASSEMBLY     * PROP_MASS
    phases['LaunchCampaign'] = C_CAMPAIGN     * PROP_MASS
    phases['Launch']          = C_LAUNCH       * PROP_MASS / 1000.0   # kg/kg * Mg -> Gg
    phases['Reentry']         = 0.0
    phases['Recovery']        = C_RECOVERY     * DOWNRANGE_KM
    phases['Maintenance']     = C_MAINTENANCE  * recovered_dry

    total = sum(phases.values())

    print_phase_table(phases, 'Falcon 9 phase GWP100 per launch, aviation CFs (Gg)')

    fleet_Tg = total * LAUNCHES / 1000.0
    print("\nPer launch : %.3f Gg  = %.1f Mg CO2eq" % (total, total * 1000))
    print("Fleet (%d launches) : %.3f Tg" % (LAUNCHES, fleet_Tg))

    return phases, total, fleet_Tg


def reproduce_high_alt():
    """High-altitude-CF scenario (CC*): only Launch and Reentry change;
    all ground-level phases keep their aviation coefficients."""
    amortised_dry = DRY_MASS_BOOSTER / REUSES + DRY_MASS_SECOND
    recovered_dry = DRY_MASS_BOOSTER

    phases = {}
    phases['Production']      = C_PRODUCTION          * amortised_dry
    phases['Propellant']      = C_PROPELLANT          * PROP_MASS / 1000.0   # unchanged
    phases['Assembly']        = C_ASSEMBLY            * PROP_MASS
    phases['LaunchCampaign'] = C_CAMPAIGN            * PROP_MASS
    phases['Launch']          = C_LAUNCH_HI_WITH_H2O  * PROP_MASS / 1000.0   # high-alt CFs
    phases['Reentry']         = REENTRY_Gg_PER_LAUNCH                         # S2 Al2O3
    phases['Recovery']        = C_RECOVERY            * DOWNRANGE_KM
    phases['Maintenance']     = C_MAINTENANCE         * recovered_dry

    total = sum(phases.values())

    print_phase_table(phases, 'Falcon 9 phase GWP100 per launch, high-altitude CFs (Gg)')

    fleet_Tg = total * LAUNCHES / 1000.0
    print("\nPer launch : %.2f Gg" % total)
    print("Fleet (%d launches) : %.1f Tg" % (LAUNCHES, fleet_Tg))

    return phases, total, fleet_Tg


def save_phases_aviation_to_json(phases, total, fleet_Tg):
    share = {ph: round(100.0 * phases[ph] / total, 2) for ph in PHASE_ORDER if total}
    # BC uncertainty band (EI(BC) 10-30 g/kg): only Launch scales with the
    # per-kg GWP; all ground phases are BC-independent.
    _non_launch_Gg = total - phases["Launch"]
    _band_total_Gg = [round(_non_launch_Gg + c * PROP_MASS / 1000.0, 3)
                      for c in BC_SWEEP_AV]
    out = {
        "scenario": "aviation CFs (CC)",
        "launcher": "Falcon 9 (kerosene/LOX), Starlink",
        "inputs": {
            "dry_mass_booster_Mg": DRY_MASS_BOOSTER,
            "dry_mass_second_Mg": DRY_MASS_SECOND,
            "propellant_Mg": PROP_MASS,
            "reuses": REUSES,
            "launches": LAUNCHES,
            "O_F": O_F,
            "downrange_km": DOWNRANGE_KM,
            "rp1_production_kg_per_kg": RP1_PRODUCTION,
            "lox_production_kg_per_kg": LOX_PRODUCTION,
        },
        "phase_order": PHASE_ORDER,
        "per_launch_phase_Gg": {ph: round(phases[ph], 3) for ph in PHASE_ORDER},
        "per_launch_phase_share_pct": {ph: share[ph] for ph in PHASE_ORDER},
        "total_per_launch_Gg": round(total, 3),
        "fleet_Tg": round(fleet_Tg, 3),
        "bc_band": {
            "EI_g_per_kg": BC_SWEEP_EI,
            "aviation_kg_per_kg": BC_SWEEP_AV,
            "total_per_launch_Gg": _band_total_Gg,
        },
    }
    with open(script_dir/"falcon9_phase_gwp100_aviation.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nSaved to falcon9_phase_gwp100_aviation.json")


def save_phases_high_alt_to_json(phases, total, fleet_Tg):
    share = {ph: round(100.0 * phases[ph] / total, 2) for ph in PHASE_ORDER if total}
    # BC uncertainty band (EI(BC) 10-30 g/kg): only Launch scales with the
    # per-kg GWP; ground + reentry phases are BC-independent.
    _non_launch_Gg = total - phases["Launch"]
    _band_total_Gg = [round(_non_launch_Gg + c * PROP_MASS / 1000.0, 3)
                      for c in BC_SWEEP_HI]
    out = {
        "scenario": "high-altitude CFs (CC*)",
        "launcher": "Falcon 9 (kerosene/LOX), Starlink",
        "inputs": {
            "dry_mass_booster_Mg": DRY_MASS_BOOSTER,
            "dry_mass_second_Mg": DRY_MASS_SECOND,
            "propellant_Mg": PROP_MASS,
            "reuses": REUSES,
            "launches": LAUNCHES,
            "O_F": O_F,
            "downrange_km": DOWNRANGE_KM,
            "rp1_production_kg_per_kg": RP1_PRODUCTION,
            "lox_production_kg_per_kg": LOX_PRODUCTION,
        },
        "launch_GWP_kg_per_kg_highalt": C_LAUNCH_HI_WITH_H2O,
        "launch_GWP_kg_per_kg_highalt_no_H2O": C_LAUNCH_HI,
        "reentry_Gg_per_launch": round(REENTRY_Gg_PER_LAUNCH, 3),
        "phase_order": PHASE_ORDER,
        "per_launch_phase_Gg": {ph: round(phases[ph], 3) for ph in PHASE_ORDER},
        "per_launch_phase_share_pct": {ph: share[ph] for ph in PHASE_ORDER},
        "total_per_launch_Gg": round(total, 3),
        "fleet_Tg": round(fleet_Tg, 3),
        "bc_band": {
            "EI_g_per_kg": BC_SWEEP_EI,
            "high_altitude_kg_per_kg": BC_SWEEP_HI,
            "total_per_launch_Gg": _band_total_Gg,
        },
    }
    with open(script_dir/"falcon9_phase_gwp100_highalt.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Saved to falcon9_phase_gwp100_highalt.json")


if __name__ == '__main__':
    phases_av, total_av, fleet_av = reproduce_aviation()
    save_phases_aviation_to_json(phases_av, total_av, fleet_av)

    phases_hi, total_hi, fleet_hi = reproduce_high_alt()
    save_phases_high_alt_to_json(phases_hi, total_hi, fleet_hi)
