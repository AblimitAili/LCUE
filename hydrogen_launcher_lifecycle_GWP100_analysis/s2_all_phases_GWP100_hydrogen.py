"""
Recover per-launcher GWP100 phase breakdown for the hydrogen (LH2 VTVL) fleet.

Repurposed from all_phases_GWP100_methane2.py for the LH2 VTVL L&XXL fleet.

Reference: Dominguez Calabuig et al., "Environmental life cycle assessment of
reusable launch vehicle fleets", Acta Astronautica 221 (2024).
  - Table 5 : per-launch total GWP100 (Gg, aviation CFs)
  - Table 6 : fleet total CC = 2.684 Tg (aviation) / CC* = 159.673 Tg (high-alt)
  - Fig. 5  : fleet-level phase fractions (LH2 VTVL L&XXL, aviation CFs, sum to 1)

Method (same as the methane script): assume each phase scales with a single
driver, derive the per-unit coefficient from the fleet total, apply per launcher,
and cross-check the per-launch sums against Table 5.

Two changes vs the methane template:
  1. SIZE-SCALED drivers: Launch Campaign and Assembly scale with propellant
     mass (mp) instead of flat per-launch (n). The paper's "recurrent activities
     independent of stage size" assumption over-charges the small L-RLV (a +25%
     overshoot vs Table 5); scaling by size removes it (see Sec. 4.2 of the
     paper, which itself flags this limitation for small launchers).
  2. Launch term = PHYSICAL (instantaneous H2O CF), NOT force-matched to CC*.

High-altitude scenario (CC*): only two phases change vs the aviation baseline:
  Launch  -> altitude-resolved high-alt CFs. For hydrogen this is H2O-dominated.
  Reentry -> upper-stage Al2O3 (CF 2.79e5); 25% of CC* (user-provided).
All other (ground-level) phases keep their aviation coefficients.

The launch term used here is the PHYSICAL value (902.1 kg/kg) from the
launch-phase emission model (instantaneous H2O CF = 1480). It is NOT forced
to reproduce Table 6 CC*: with reentry = 25% of CC* and the ground phases at
aviation CFs, the fleet total overshoots CC* by ~19%. That overshoot is the
H2O-CF uncertainty - the paper's caveat that high-altitude CFs "should be
applied to the relaxed radiative forcing after stratospheric adjustment"
(Sec. 4.4). This mirrors how the methane script keeps its own H2O-included
launch term and reports the resulting deviation.

KNOWN INPUTS
  - Table 6 CC  = 2.684 Tg     (aviation CFs)
  - Table 6 CC* = 159.673 Tg   (high-alt CFs)
  - Table 5 : L-RLV 4.71, XXL-RLV 12.49, XXL-RLV exp. core 13.99 Gg (aviation)
  - Fig. 5  : phase fractions (aviation CFs)
  - Table 1 : propellant, dry masses, reuse count, recovery distances, launches
  - Table 4 + launch model : launch GWP100 (aviation & high-alt)
"""

"""
Recover per-launcher GWP100 phase breakdown for the hydrogen (LH2 VTVL) fleet.

Repurposed from all_phases_GWP100_methane2.py for the LH2 VTVL L&XXL fleet.

Reference: Dominguez Calabuig et al., "Environmental life cycle assessment of
reusable launch vehicle fleets", Acta Astronautica 221 (2024).
  - Table 5 : per-launch total GWP100 (Gg, aviation CFs)
  - Table 6 : fleet total CC = 2.684 Tg (aviation) / CC* = 159.673 Tg (high-alt)
  - Fig. 5  : fleet-level phase fractions (LH2 VTVL L&XXL, aviation CFs, sum to 1)

Method (same as the methane script): assume each phase scales with a single
driver, derive the per-unit coefficient from the fleet total, apply per launcher,
and cross-check the per-launch sums against Table 5.

Two changes vs the methane template:
  1. SIZE-SCALED drivers: Launch Campaign and Assembly scale with propellant
     mass (mp) instead of flat per-launch (n). The paper's "recurrent activities
     independent of stage size" assumption over-charges the small L-RLV (a +25%
     overshoot vs Table 5); scaling by size removes it (see Sec. 4.2 of the
     paper, which itself flags this limitation for small launchers).
  2. Launch term = PHYSICAL (instantaneous H2O CF), NOT force-matched to CC*.

High-altitude scenario (CC*): only two phases change vs the aviation baseline:
  Launch  -> altitude-resolved high-alt CFs. For hydrogen this is H2O-dominated.
  Reentry -> upper-stage Al2O3 (CF 2.79e5); 25% of CC* (user-provided).
All other (ground-level) phases keep their aviation coefficients.

The launch term used here is the PHYSICAL value (902.1 kg/kg) from the
launch-phase emission model (instantaneous H2O CF = 1480). It is NOT forced
to reproduce Table 6 CC*: with reentry = 25% of CC* and the ground phases at
aviation CFs, the fleet total overshoots CC* by ~19%. That overshoot is the
H2O-CF uncertainty - the paper's caveat that high-altitude CFs "should be
applied to the relaxed radiative forcing after stratospheric adjustment"
(Sec. 4.4). This mirrors how the methane script keeps its own H2O-included
launch term and reports the resulting deviation.

KNOWN INPUTS
  - Table 6 CC  = 2.684 Tg     (aviation CFs)
  - Table 6 CC* = 159.673 Tg   (high-alt CFs)
  - Table 5 : L-RLV 4.71, XXL-RLV 12.49, XXL-RLV exp. core 13.99 Gg (aviation)
  - Fig. 5  : phase fractions (aviation CFs)
  - Table 1 : propellant, dry masses, reuse count, recovery distances, launches
  - Table 4 + launch model : launch GWP100 (aviation & high-alt)
"""

import json
from pathlib import Path
script_dir = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
FLEET_TOTAL_TG = 2.684        # fleet GWP100 (aviation CFs), Tg  (Table 6 CC)

# Fig. 5 - fleet-level phase fractions (GWP100, aviation CFs), LH2 VTVL L&XXL
FIG5 = {
    'Production':      0.121,
    'Propellant':      0.474,
    'LaunchCampaign': 0.096,
    'Assembly':        0.091,
    'Recovery':        0.126,
    'Maintenance':     0.059,
    'Reentry':         0.000,
    'Launch':          0.033,
}

# Fixed display / output order for Table 2.
PHASE_ORDER = [
    'Production',
    'Propellant',
    'Assembly',
    'LaunchCampaign',
    'Launch',
    'Reentry',
    'Recovery',
    'Maintenance',
]

# Table 5 of the paper - per-launch total GWP100 (Gg), aviation CFs
TABLE5 = {'L-RLV': 4.71, 'XXL-RLV': 12.49, 'XXL-RLV exp. core': 13.99}

# Table 1 - block dry masses (Mg) and reuse count (LH2 VTVL fleet)
DRY_H240 = 25.675          # first-stage / booster / core dry mass
DRY_H61 = 6.068            # upper stage dry mass
REUSES = 15                # n_r, first stage only (upper stage is expendable)

# Each launcher: driver values used by the scaling model.
#   n     : number of launches
#   mp    : total propellant mass (Mg)         -> drives Launch, Propellant
#   amort : amortised dry mass (Mg)            -> drives Production
#   dist  : recovered downrange distance (km)  -> drives Recovery
#   rec   : recovered dry mass per flight (Mg) -> drives Maintenance
LAUNCHERS = {
    'L-RLV': {
        'n': 55.4, 'mp': 240 + 61,
        'amort': (DRY_H240 / REUSES + DRY_H61),          # core reused, upper expended
        'dist': 740,                                     # 1 core at 740 km
        'rec': DRY_H240,
    },
    'XXL-RLV': {
        'n': 145.1, 'mp': 3 * 240 + 61,
        'amort': (3 * DRY_H240 / REUSES + DRY_H61),      # 2 boosters + core reused
        'dist': 1511 + 2 * 1160,                         # core 1511 + 2 boosters x 1160
        'rec': 3 * DRY_H240,
    },
    'XXL-RLV exp. core': {
        'n': 43.7, 'mp': 3 * 240 + 61,
        'amort': (2 * DRY_H240 / REUSES + DRY_H240 + DRY_H61),  # core expended
        'dist': 2 * 1160,                                # 2 boosters x 1160
        'rec': 2 * DRY_H240,
    },
}

# Which driver each phase scales with.
# Launch Campaign and Assembly are SIZE-SCALED (per Mg propellant) instead of
# flat per-launch ('n'). Rationale: the paper's size-independence assumption for
# recurrent activities over-charges the small L-RLV (see the +25% overshoot) -
# small launchers have easier handling/campaign considerations (paper Sec. 4.2).
PHASE_DRIVER = {
    'Launch':          'mp',
    'Propellant':      'mp',
    'Production':      'amort',
    'Recovery':        'dist',
    'Maintenance':     'rec',
    'LaunchCampaign': 'mp',   # size-scaled (was flat 'n')
    'Assembly':        'mp',   # size-scaled (was flat 'n')
    'Reentry':         'n',    # one upper-stage demise per flight: 0 (av) / non-zero (high-alt)
}


# ---------------------------------------------------------------------------
# High-altitude scenario (CC*) inputs
# ---------------------------------------------------------------------------
TABLE6_CCSTAR = 159.673   # fleet total, high-altitude CFs [Tg]  (Table 6 CC*)

# Launch phase, altitude-resolved high-altitude CFs - READ from the launch model
# output (launch_gwp100_species_hydrogen.json), not hardcoded. Requires
# s1_launch_phase_GWP100_hydrogen.py to have been run first.
#   physical (with H2O) = 902.103 kg/kg  (instantaneous H2O CF = 1480)
#   H2O term            = 901.410 kg/kg  (99.9% of launch; high CF uncertainty)
#   H2O-excluded        =   0.693 kg/kg  (only H2 + NOx; tiny for hydrogen)
with open(script_dir / "launch_gwp100_species_hydrogen.json", encoding="utf-8") as f:
    _prom = json.load(f)["Prometheus-H"]
C_LAUNCH_HI_PHYSICAL = _prom["total_high_altitude_kg_per_kg"]       # kg/kg (with H2O)
C_LAUNCH_HI_NO_H2O   = (_prom["total_high_altitude_kg_per_kg"]
                        - _prom["high_altitude"]["H2O"] / 1000.0)  # kg/kg (H2O-excluded)

# Reentry (upper-stage H61 demise, Al2O3 + NOx): user-provided value = 25% of CC*.
# 25% of CC* = 39.9 Tg, mass-consistent with the CH4 fleet's reentry (~43 Tg):
# reentry scales with upper-stage dry mass x launches, which are nearly identical
# for the H61 (6.07 Mg) and M110 (6.30 Mg) upper stages.
REENTRY_FRACTION = 0.25  # from figure 8 of the first reference
REENTRY_FLEET_TG = TABLE6_CCSTAR * REENTRY_FRACTION

# Fleet propellant mass (Mg), used to convert Tg <-> Gg/Mg <-> kg/kg
FLEET_MP = sum(d['mp'] * d['n'] for d in LAUNCHERS.values())

# Ground-phase fleet total (all phases except Launch and Reentry), aviation CFs,
# which are UNCHANGED in the high-altitude scenario [Tg].
GROUND_TG = sum(FIG5[ph] * FLEET_TOTAL_TG for ph in FIG5
                if ph not in ('Launch', 'Reentry'))

# CC*-matched launch coefficient [kg/kg] - REFERENCE ONLY, NOT USED.
# The launch GWP that would force launch + reentry + ground = CC* exactly.
# Kept to document the implied H2O-CF reduction (~21%); we do NOT force-match.
# Units: (Tg) * 1e6 = Mg-equiv / FLEET_MP(Mg) = kg/kg.
C_LAUNCH_HI_MATCHED = (TABLE6_CCSTAR - REENTRY_FLEET_TG - GROUND_TG) * 1e6 / FLEET_MP


# ---------------------------------------------------------------------------
# Derive coefficients and recover per-launcher values
# ---------------------------------------------------------------------------
def fleet_driver_sum(driver):
    if driver == 'n':
        return sum(d['n'] for d in LAUNCHERS.values())
    return sum(d[driver] * d['n'] for d in LAUNCHERS.values())


def coefficient(phase):
    driver = PHASE_DRIVER[phase]
    fleet_gwp_Gg = FIG5[phase] * FLEET_TOTAL_TG * 1000   # Tg -> Gg
    return fleet_gwp_Gg / fleet_driver_sum(driver)


def compute_share(rows):
    """Phase share (%) of the per-launch total, for each launcher."""
    share = {}
    for la, phases in rows.items():
        total = sum(phases.values())
        share[la] = {
            ph: (100.0 * g / total if total else 0.0)
            for ph, g in phases.items()
        }
    return share


def print_phase_tables(rows, title):
    """Per-launcher table: Phase | GWP100 (Gg) | Share (%), in PHASE_ORDER."""
    share = compute_share(rows)
    print('\n' + title)
    for la in LAUNCHERS:
        print('\n%s' % la)
        print('%-18s %18s %10s' % ('Phase', 'GWP100 (Gg CO2eq)', 'Share'))
        print('-' * 48)
        for ph in PHASE_ORDER:
            gwp = rows[la].get(ph, 0.0)
            pct = share[la].get(ph, 0.0)
            print('%-18s %18.2f %9.1f%%' % (ph, gwp, pct))
        total = sum(rows[la].values())
        print('-' * 48)
        print('%-18s %18.2f %9.1f%%' % ('Total', total, 100.0))


def reproduce_aviation():
    coeffs = {ph: coefficient(ph) for ph in FIG5}

    print('Aviation-Based Phase GWP100 Coefficients  (Gg per driver unit):')
    for ph in PHASE_ORDER:
        print('  %-18s %.4f  (per %s)' % (ph, coeffs[ph], PHASE_DRIVER[ph]))

    rows = {}
    for la, d in LAUNCHERS.items():
        rows[la] = {}
        for ph, drv in PHASE_DRIVER.items():
            rows[la][ph] = coeffs[ph] if drv == 'n' else coeffs[ph] * d[drv]

    print_phase_tables(rows, 'Aviation-Based Per-launch phase GWP100 (Gg)')

    print('\nValidation vs Table 5 (aviation CFs):')
    print('%-22s %10s %10s %10s' % ('launcher', 'SUM (Gg)', 'Table5', 'delta'))
    for la in LAUNCHERS:
        s = sum(rows[la].values())
        print('%-22s %10.2f %10.2f %+9.1f%%'
              % (la, s, TABLE5[la], 100 * (s / TABLE5[la] - 1)))

    return coeffs, rows


def reproduce_high_alt():
    coeffs = {ph: coefficient(ph) for ph in FIG5}
    coeffs['Launch'] = C_LAUNCH_HI_PHYSICAL / 1000.0                 # kg/kg -> Gg/Mg
    coeffs['Reentry'] = REENTRY_FLEET_TG * 1000.0 / fleet_driver_sum('n')  # Gg/launch

    print('\nHigh-altitude coefficients (Gg per driver unit):')
    for ph in PHASE_ORDER:
        print('  %-18s %.4f  (per %s)' % (ph, coeffs[ph], PHASE_DRIVER[ph]))

    rows = {}
    for la, d in LAUNCHERS.items():
        rows[la] = {}
        for ph, drv in PHASE_DRIVER.items():
            rows[la][ph] = coeffs[ph] if drv == 'n' else coeffs[ph] * d[drv]

    print_phase_tables(rows, 'High-altitude Per-launch phase GWP100 (Gg)')

    fleet_hi_Gg = sum(sum(rows[la].values()) * LAUNCHERS[la]['n'] for la in LAUNCHERS)
    fleet_hi_Tg = fleet_hi_Gg / 1000.0
    print('\nFleet total (high-altitude CFs):')
    print('  model       = %.1f Tg' % fleet_hi_Tg)
    print('  Table 6 CC* = %.1f Tg' % TABLE6_CCSTAR)
    print('  deviation   = %+.1f%%  (H2O-CF uncertainty: physical launch overshoots CC*)'
          % (100 * (fleet_hi_Tg / TABLE6_CCSTAR - 1)))
    print('  (launch = physical %.1f kg/kg; reentry = %.1f Tg = %.1f%% of CC*)'
          % (C_LAUNCH_HI_PHYSICAL, REENTRY_FLEET_TG, 100 * REENTRY_FRACTION))

    return coeffs, rows


def print_h2o_uncertainty():
    """Document the H2O-CF uncertainty implied by the CC* overshoot (NOT applied)."""
    print('\n=== H2O-CF uncertainty (physical launch vs CC*) ===')
    print('  physical launch (instantaneous H2O CF = 1480) = %.1f kg/kg' % C_LAUNCH_HI_PHYSICAL)
    print('  CC*-matched launch (what would reproduce CC*)  = %.1f kg/kg' % C_LAUNCH_HI_MATCHED)
    print('  implied H2O-term reduction                     = %.1f%%'
          % (100 * (1 - C_LAUNCH_HI_MATCHED / C_LAUNCH_HI_PHYSICAL)))
    print('  -> NOT applied (no force-matching). Kept as documentation of the')
    print('     paper\'s caveat: high-alt CFs "should be applied to the relaxed')
    print('     radiative forcing after stratospheric adjustment" (Sec. 4.4).')


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------
def save_phases_aviation_to_json(coeffs, rows):
    share = compute_share(rows)
    data = {
        "scenario": "aviation CFs (CC)",
        "fleet_total_Tg": FLEET_TOTAL_TG,
        "table5_Gg": TABLE5,
        "phase_order": PHASE_ORDER,
        "phase_driver": dict(PHASE_DRIVER),
        "coefficients_Gg_per_driver_unit": {
            ph: round(coeffs[ph], 6) for ph in PHASE_ORDER
        },
        "per_launcher_phase_Gg": {
            la: {ph: round(rows[la][ph], 3) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_phase_share_pct": {
            la: {ph: round(share[la][ph], 2) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_sum_Gg": {
            la: round(sum(rows[la].values()), 3) for la in LAUNCHERS
        },
    }
    RESULTS_JSON = "phases_gwp100_hydrogen_launchers_aviation.json"
    with open(script_dir / RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved aviation phase GWP100 to {RESULTS_JSON}")


def save_phases_high_alt_to_json(coeffs, rows):
    share = compute_share(rows)
    fleet_hi_Tg = sum(sum(rows[la].values()) * LAUNCHERS[la]['n'] for la in LAUNCHERS) / 1000.0
    data = {
        "scenario": "high-altitude CFs (CC*)",
        "fleet_total_CCstar_Tg": TABLE6_CCSTAR,
        "fleet_total_model_Tg": round(fleet_hi_Tg, 3),
        "deviation_vs_CCstar_pct": round(100 * (fleet_hi_Tg / TABLE6_CCSTAR - 1), 2),
        "launch_GWP_kg_per_kg_highalt_USED_physical": C_LAUNCH_HI_PHYSICAL,
        "launch_GWP_kg_per_kg_highalt_CCstar_matched_reference": C_LAUNCH_HI_MATCHED,
        "launch_GWP_kg_per_kg_highalt_no_H2O": C_LAUNCH_HI_NO_H2O,
        "reentry_fleet_Tg": REENTRY_FLEET_TG,
        "reentry_fraction_of_CCstar": REENTRY_FRACTION,
        "phase_order": PHASE_ORDER,
        "coefficients_Gg_per_driver_unit": {
            ph: round(coeffs[ph], 6) for ph in PHASE_ORDER
        },
        "per_launcher_phase_highalt_Gg": {
            la: {ph: round(rows[la][ph], 3) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_phase_share_highalt_pct": {
            la: {ph: round(share[la][ph], 2) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_sum_highalt_Gg": {
            la: round(sum(rows[la].values()), 3) for la in LAUNCHERS
        },
    }
    RESULTS_JSON = "phases_gwp100_hydrogen_launchers_highalt.json"
    with open(script_dir / RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved high-alt phase GWP100 to {RESULTS_JSON}")


if __name__ == '__main__':
    coeffs_av, rows_av = reproduce_aviation()
    save_phases_aviation_to_json(coeffs_av, rows_av)

    coeffs_hi, rows_hi = reproduce_high_alt()
    save_phases_high_alt_to_json(coeffs_hi, rows_hi)

    print_h2o_uncertainty()

