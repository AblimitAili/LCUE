"""
s2_Orbital — Reanalyse the orbital DC scope-3 onetime emissions for each launcher
scenario defined in `scenarios.json`, and write one reanalysis JSON + one pie
chart per scenario.

Reads:  Orbital_DC_emissions_<name>.json  (from s1)
Writes: Orbital_DC_emissions_reanalysis_<name>.json
        Scope3_Onetime_Emissions_PieChart_<name>.svg
"""

import json
import matplotlib.pyplot as plt
from pathlib import Path

script_dir = Path(__file__).resolve().parent

# with open("scenarios.json") as _f:
#     SCENARIOS = json.load(_f)["scenarios"]

from s0_scenarios import SCENARIOS
SCENARIOS = [s for s in SCENARIOS if s.get("enabled", True)]


def reanalyse(item):
    """Add the onetime/E2 ratio and scope-3 emission fractions to one scenario."""
    Es3_onetime_energy = item['Es3_onetime_energy']
    item['Es3_onetime_to_E2_ratio'] = round(
        sum(Es3_onetime_energy.values()) / item['Es2_energy'], 2)

    Cs3_onetime_emissions = {}
    for k, v in Es3_onetime_energy.items():
        Cs3_onetime_emissions[k] = round(v * item['scope3_carbon_intensity'], 0)
    item['Cs3_onetime_emissions'] = Cs3_onetime_emissions

    total = sum(Cs3_onetime_emissions.values())
    item['Cs3_onetime_fractions'] = {
        k: round(v / total, 2) for k, v in Cs3_onetime_emissions.items()}
    return item


def make_pie_chart(name, item):
    labels = {
        'capital_server': 'Server Manufacturing',
        'capital_satellite': 'Satellite Manufacturing',
        'upstream_transport': 'Launch-Related Activities',
    }
    emissions = item['Cs3_onetime_emissions']
    values = [emissions[k] for k in labels]
    names = [labels[k] for k in labels]

    plt.figure()
    plt.pie(values, labels=names, autopct='%1.1f%%',
            colors=['#4C72B0', '#DD8452', '#55A868'], startangle=90)
    plt.title(f"Scope-3 onetime emissions — {name}")
    plt.savefig(script_dir/f'Scope3_Onetime_Emissions_PieChart_{name}.svg',
                bbox_inches='tight')
    # plt.close()
    plt.show()


if __name__ == '__main__':
    for sc in SCENARIOS:
        name = sc["name"]
        with open(script_dir/f'Orbital_DC_emissions_{name}.json', 'r', encoding="utf-8") as f:
            parameters = json.load(f)

        for key, item in parameters.items():
            item = reanalyse(item)

        with open(script_dir/f'Orbital_DC_emissions_reanalysis_{name}.json', 'w', encoding="utf-8") as f:
            json.dump(parameters, f, indent=4)

        make_pie_chart(name, list(parameters.values())[0])
        ratio = list(parameters.values())[0]['Es3_onetime_to_E2_ratio']
        print(f'{name:15s} {sc["label"]:28s} -> Es3_onetime/E2 = {ratio}')
