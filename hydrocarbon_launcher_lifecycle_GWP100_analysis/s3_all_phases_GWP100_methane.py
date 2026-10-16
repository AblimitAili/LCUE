"""
Recover per-launcher GWP100 phase breakdown for the methane (LCH4) fleet.
Reference: Environmental life cycle assessment of reusable launch vehicle fleets:
Large climate impact driven by rocket exhaust emissions
            https://doi.org/10.1016/j.actaastro.2024.05.009

Problem: Figure 6 reports each LCA phase only as a FLEET-LEVEL fraction
(lumped over the three launchers). To split it per launcher we must assume
each phase scales with a single driver. This script derives the per-unit
coefficient for each phase from the fleet total, then applies it per launcher,
and cross-checks the per-launch sums against Table 5.

It also reproduces the high-altitude (CC*) scenario, where only the
stratospheric phases change (Launch -> altitude-resolved high-alt CFs;
Reentry -> upper-stage Al2O3), while all ground-level phases keep their
aviation coefficients.

Known inputs:
  - Table 6 (CC,  aviation CFs): fleet total = 6.016 Tg
  - Table 6 (CC*, high-alt CFs): fleet total = 1229.818 Tg
  - Figure 6 : fleet-level phase fractions (aviation CFs, sum to 1.0)
  - Table 5  : per-launch total GWP100 (Gg, aviation CFs)
  - Table 1  : launches, propellant mass, dry masses, recovery distances
"""

import json
from pathlib import Path
script_dir = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
FLEET_TOTAL_TG = 6.016        # fleet GWP100 (aviation CFs), Tg  (Table 6 CC)

FIG6 = {
    'Production':      0.080,
    'Propellant':      0.473,
    'LaunchCampaign': 0.050,
    'Assembly':        0.050,
    'Recovery':        0.061,
    'Maintenance':     0.032,
    'Reentry':         0.000,
    'Launch':          0.254,
}

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

TABLE5 = {'L-RVL': 10.36, 'XXL': 27.74, 'XXL-exp': 29.60}

DRY_M520 = 30.435
DRY_M110 = 6.299
REUSES = 15

LAUNCHERS = {
    'L-RVL': {
        'n': 65.1, 'mp': 630,
        'amort': (DRY_M520 / REUSES + DRY_M110),
        'dist': 650,
        'rec': DRY_M520,
    },
    'XXL': {
        'n': 121.5, 'mp': 1670,
        'amort': (3 * DRY_M520 / REUSES + DRY_M110),
        'dist': 3418,
        'rec': 3 * DRY_M520,
    },
    'XXL-exp': {
        'n': 66.6, 'mp': 1670,
        'amort': (2 * DRY_M520 / REUSES + DRY_M520 + DRY_M110),
        'dist': 1948,
        'rec': 2 * DRY_M520,
    },
}

PHASE_DRIVER = {
    'Launch':          'mp',
    'Propellant':      'mp',
    'Production':      'amort',
    'Recovery':        'dist',
    'Maintenance':     'rec',
    'LaunchCampaign': 'mp',
    'Assembly':        'mp',
    'Reentry':         'n',
}

# ---------------------------------------------------------------------------
# High-altitude scenario (CC*) inputs
# ---------------------------------------------------------------------------
TABLE6_CCSTAR = 1229.818
REENTRY_FRACTION = 0.035

with open(script_dir / "launch_gwp100_species.json", encoding="utf-8") as f:
    _meth = json.load(f)["methane"]
C_LAUNCH_HI_WITH_H2O = sum(_meth["high_altitude"].values()) / 1000.0
C_LAUNCH_HI          = C_LAUNCH_HI_WITH_H2O - _meth["high_altitude"]["H2O"] / 1000.0

REENTRY_FLEET_TG = TABLE6_CCSTAR * REENTRY_FRACTION


# ---------------------------------------------------------------------------
# Derive coefficients and recover per-launcher values
# ---------------------------------------------------------------------------
def fleet_driver_sum(driver):
    if driver == 'n':
        return sum(d['n'] for d in LAUNCHERS.values())
    return sum(d[driver] * d['n'] for d in LAUNCHERS.values())


def coefficient(phase):
    driver = PHASE_DRIVER[phase]
    fleet_gwp_Gg = FIG6[phase] * FLEET_TOTAL_TG * 1000   # Tg -> Gg
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
    """Per-launcher table: Phase | GWP100 (Gg) | Share, in PHASE_ORDER."""
    share = compute_share(rows)
    print('\n' + title)
    for la in LAUNCHERS:
        print('\n%s' % la)
        print('%-18s %18s %10s' % ('Phase', 'GWP100 (Gg CO2eq)', 'Share'))
        print('-' * 48)
        for ph in PHASE_ORDER:
            g = rows[la].get(ph, 0.0)
            pct = share[la].get(ph, 0.0)
            print('%-18s %18.2f %9.1f%%' % (ph, g, pct))
        total = sum(rows[la].values())
        print('-' * 48)
        print('%-18s %18.2f %9.1f%%' % ('Total', total, 100.0))


def reproduce_aviation():
    coeffs = {ph: coefficient(ph) for ph in FIG6}

    print('Aviation-Based Phase GWP100 Coefficients (Gg per driver unit):')
    for ph in PHASE_ORDER:
        print('  %-18s %.4f  (per %s)' % (ph, coeffs[ph], PHASE_DRIVER[ph]))

    rows = {}
    for la, d in LAUNCHERS.items():
        rows[la] = {}
        for ph, drv in PHASE_DRIVER.items():
            rows[la][ph] = coeffs[ph] if drv == 'n' else coeffs[ph] * d[drv]

    print_phase_tables(rows, 'Aviation-Based Per-launch phase GWP100 (Gg)')

    print('\nCross-check vs Table 5:')
    print('%-16s' % 'Table5' + ''.join('%22.2f' % TABLE5[la] for la in LAUNCHERS))
    print('%-16s' % 'delta' + ''.join(
        '%22.1f%%' % (100 * (sum(rows[la].values()) / TABLE5[la] - 1)) for la in LAUNCHERS))

    return coeffs, rows


def reproduce_high_alt():
    coeffs = {ph: coefficient(ph) for ph in FIG6}
    coeffs['Launch']  = C_LAUNCH_HI_WITH_H2O / 1000.0
    coeffs['Reentry'] = REENTRY_FLEET_TG * 1000.0 / fleet_driver_sum('n')

    print('\nHigh-altitude coefficients (Gg per driver unit):')
    for ph in PHASE_ORDER:
        print('  %-18s %.4f  (per %s)' % (ph, coeffs[ph], PHASE_DRIVER[ph]))

    rows = {}
    for la, d in LAUNCHERS.items():
        rows[la] = {}
        for ph, drv in PHASE_DRIVER.items():
            rows[la][ph] = coeffs[ph] if drv == 'n' else coeffs[ph] * d[drv]

    print_phase_tables(rows, 'Per-launch phase GWP100 under high-altitude CFs (Gg)')

    fleet_hi_Gg = sum(sum(rows[la].values()) * LAUNCHERS[la]['n'] for la in LAUNCHERS)
    fleet_hi_Tg = fleet_hi_Gg / 1000.0
    print('\nFleet total (high-altitude CFs):')
    print('  model       = %.1f Tg' % fleet_hi_Tg)
    print('  Table 6 CC* = %.1f Tg' % TABLE6_CCSTAR)
    print('  deviation   = %+.1f%%' % (100 * (fleet_hi_Tg / TABLE6_CCSTAR - 1)))
    print('  (launch uses H2O-included value %.0f g/kg; reentry = %.0f Tg)'
          % (C_LAUNCH_HI_WITH_H2O * 1000, REENTRY_FLEET_TG))

    return coeffs, rows, fleet_hi_Tg


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
        "coefficients_Gg_per_driver_unit": {ph: round(coeffs[ph], 4) for ph in PHASE_ORDER},
        "per_launcher_phase_Gg": {
            la: {ph: round(rows[la][ph], 3) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_phase_share_pct": {
            la: {ph: round(share[la][ph], 2) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_sum_Gg": {la: round(sum(rows[la].values()), 3) for la in LAUNCHERS},
    }
    RESULTS_JSON = script_dir / "phases_gwp100_methane_launchers_aviation.json"
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved aviation phase GWP100 to {RESULTS_JSON}")


def save_phases_high_alt_to_json(coeffs, rows, fleet_hi_Tg):
    share = compute_share(rows)
    data = {
        "scenario": "high-altitude CFs (CC*)",
        "fleet_total_CCstar_Tg": TABLE6_CCSTAR,
        "fleet_total_model_Tg": round(fleet_hi_Tg, 3),
        "deviation_vs_CCstar_pct": round(100 * (fleet_hi_Tg / TABLE6_CCSTAR - 1), 2),
        "launch_GWP_kg_per_kg_highalt": C_LAUNCH_HI_WITH_H2O,
        "launch_GWP_kg_per_kg_highalt_no_H2O": C_LAUNCH_HI,
        "reentry_fleet_Tg": REENTRY_FLEET_TG,
        "phase_order": PHASE_ORDER,
        "coefficients_Gg_per_driver_unit": {ph: round(coeffs[ph], 4) for ph in PHASE_ORDER},
        "per_launcher_phase_highalt_Gg": {
            la: {ph: round(rows[la][ph], 3) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_phase_highalt_share_pct": {
            la: {ph: round(share[la][ph], 2) for ph in PHASE_ORDER}
            for la in LAUNCHERS
        },
        "per_launcher_sum_highalt_Gg": {la: round(sum(rows[la].values()), 3) for la in LAUNCHERS},
    }
    RESULTS_JSON = script_dir / "phases_gwp100_methane_launchers_highalt.json"
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved high-alt phase GWP100 to {RESULTS_JSON}")


if __name__ == '__main__':
    coeffs_av, rows_av = reproduce_aviation()
    save_phases_aviation_to_json(coeffs_av, rows_av)

    coeffs_hi, rows_hi, fleet_hi_Tg = reproduce_high_alt()
    save_phases_high_alt_to_json(coeffs_hi, rows_hi, fleet_hi_Tg)
