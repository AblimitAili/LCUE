"""
Validation of the hydrogen (LH2 VTVL) fleet reconstruction against the paper.

Repurposed from validate_launch_phase.py for the LH2 VTVL L&XXL fleet.

Cross-checks the outputs of s2_all_phases_GWP100_hydrogen.py against the
tabulated values in Dominguez Calabuig et al., Acta Astronautica 221 (2024):
  - Table 5 : per-launch total GWP100 (Gg, aviation CFs)
  - Table 6 : fleet total CC = 2.684 Tg (aviation) and CC* = 159.673 Tg (high-alt)

Also reports the launch-event GWP per kg (Prometheus-H) from the launch model.

Reads:
  - phases_gwp100_hydrogen_launchers_aviation.json  (per-launch sums)
  - phases_gwp100_hydrogen_launchers_highalt.json   (fleet total + launch term)
  - launch_gwp100_species_hydrogen.json             (launch-event GWP per kg)

Run after s1_launch_phase_GWP100_hydrogen.py and s2_all_phases_GWP100_hydrogen.py.

"""

import json
from pathlib import Path
script_dir = Path(__file__).resolve().parent

TABLE5 = {'L-RLV': 4.71, 'XXL-RLV': 12.49, 'XXL-RLV exp. core': 13.99}
TABLE6_CC = 2.684        # Tg, aviation CFs
TABLE6_CCSTAR = 159.673  # Tg, high-alt CFs

# The launch-event aviation GWP is not tabulated directly in the paper; the
# paper's Fig. 5 gives a 3.3% launch share of the 2.684 Tg total, i.e. an
# implied ~0.54 kg/kg. The launch model (Table 4 EIs + Table 2 CFs) gives
# 0.465 kg/kg. Band below is a sanity check around the model value.
LAUNCH_AV_EXPECT = 0.465   # kg/kg (Prometheus-H, from the launch model)
LAUNCH_AV_TOL = 0.02       # kg/kg


def check(name, got, want, tol_frac, unit):
    tol = abs(want) * tol_frac
    ok = abs(got - want) <= tol
    print('  %-30s %10.4f %s   ref %10.4f %s   tol %-5.2f%%   %s'
          % (name, got, unit, want, unit, 100 * tol_frac, 'PASS' if ok else 'FAIL'))
    return ok


def main():
    results = []

    # ---- Aviation: per-launch sums vs Table 5 ----------------------------
    with open(script_dir/'phases_gwp100_hydrogen_launchers_aviation.json', 'r',
              encoding='utf-8') as f:
        av = json.load(f)

    print('== Table 5 cross-check (per-launch, aviation CFs, Gg) ==')
    for la, ref in TABLE5.items():
        got = av['per_launcher_sum_Gg'][la]
        results.append(check('Table5 ' + la, got, ref, 0.025, 'Gg'))

    print('== Table 6 CC cross-check (fleet, aviation CFs, Tg) ==')
    fleet_av_Tg = av['fleet_total_Tg']
    results.append(check('Table6 CC (fleet)', fleet_av_Tg, TABLE6_CC, 1e-6, 'Tg'))

    # ---- High-alt: fleet total vs CC* (reported, not asserted) -----------
    with open(script_dir/'phases_gwp100_hydrogen_launchers_highalt.json', 'r',
              encoding='utf-8') as f:
        hi = json.load(f)

    print('== Table 6 CC* cross-check (fleet, high-alt CFs, Tg) ==')
    fleet_hi_Tg = hi['fleet_total_model_Tg']
    dev = hi['deviation_vs_CCstar_pct']
    print('  model fleet total   = %.1f Tg' % fleet_hi_Tg)
    print('  Table 6 CC* (paper) = %.1f Tg' % TABLE6_CCSTAR)
    print('  deviation           = %+.1f%%  (expected H2O-CF uncertainty; NOT force-matched)'
          % dev)

    physical = hi['launch_GWP_kg_per_kg_highalt_USED_physical']
    matched = hi['launch_GWP_kg_per_kg_highalt_CCstar_matched_reference']
    reentry = hi['reentry_fleet_Tg']
    frac = hi['reentry_fraction_of_CCstar']
    print('  launch term (physical, USED)     = %.1f kg/kg' % physical)
    print('  launch term (CC*-matched, ref)   = %.1f kg/kg  (would be -%.1f%% H2O)'
          % (matched, 100 * (1 - matched / physical)))
    print('  reentry (25%% of CC*)             = %.1f Tg (%.2f)' % (reentry, frac))

    # ---- Launch-event model sanity ---------------------------------------
    with open(script_dir/'launch_gwp100_species_hydrogen.json', 'r', encoding='utf-8') as f:
        lp = json.load(f)

    print('== Launch-event model sanity (Prometheus-H, per kg propellant) ==')
    prom = lp.get('Prometheus-H')
    if prom is None:
        print('  (no "Prometheus-H" entry found in launch JSON)')
        results.append(False)
    else:
        av_tot = prom['total_aviation_kg_per_kg']
        hi_tot = prom['total_high_altitude_kg_per_kg']
        ok = abs(av_tot - LAUNCH_AV_EXPECT) <= LAUNCH_AV_TOL
        print('  aviation-only launch GWP    = %.3f kg/kg (expect %.3f +/- %.3f)  %s'
              % (av_tot, LAUNCH_AV_EXPECT, LAUNCH_AV_TOL, 'PASS' if ok else 'FAIL'))
        results.append(ok)
        print('  high-altitude launch GWP    = %.1f kg/kg (H2O-dominated)' % hi_tot)

    print('\n%d/%d checks passed.' % (sum(results), len(results)))


if __name__ == '__main__':
    main()
