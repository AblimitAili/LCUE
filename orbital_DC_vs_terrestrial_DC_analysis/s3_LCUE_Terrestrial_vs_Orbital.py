import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent


# with open("scenarios.json") as _f:
#     SCENARIOS = json.load(_f)["scenarios"]

from s0_scenarios import SCENARIOS, HYDROCARBON_DIR
SCENARIOS = [s for s in SCENARIOS if s.get("enabled", True)]

with open(script_dir/'Google_DC_emissions_reanalysis.json', 'r') as f:
    terrestrialDC_paramaters = json.load(f)

with open(script_dir/"Orbital_DC_emissions_falcon9.json") as f:
    s1_data = json.load(f)
dc = list(s1_data.values())[0]
cppk = dc["power_per_kg_in_W_kg"]

# Read every orbital reanalysis JSON (one per launcher scenario)
orbital_ratios = {}
scope3_carbon_intensity = None
falcon9_band = None   # {"delta_ratio": ...} for the EI(BC) 10-30 g/kg band
for sc in SCENARIOS:
    with open(script_dir/f'Orbital_DC_emissions_reanalysis_{sc["name"]}.json', 'r') as f:
        params = json.load(f)
    dc = list(params.values())[0]
    orbital_ratios[sc["name"]] = dc['Es3_onetime_to_E2_ratio']
    if scope3_carbon_intensity is None:
        scope3_carbon_intensity = dc['scope3_carbon_intensity']

    if sc["name"] == "falcon9":
        # EI(BC) 10-30 g/kg band: the launch term is linear in the per-launch
        # GWP, so the ratio half-width scales like the GWP half-width.
        with open(HYDROCARBON_DIR / "falcon9_phase_gwp100_aviation.json", encoding="utf-8") as f:
            f9 = json.load(f)
        band = f9["bc_band"]
        total_mean = f9["total_per_launch_Gg"]
        total_high = band["total_per_launch_Gg"][-1]        # EI(BC) = 30
        upstream = dc["Es3_onetime_energy"]["upstream_transport"]
        Es2 = dc["Es2_energy"]
        falcon9_band = {
            "delta_ratio": (upstream / Es2) * (total_high - total_mean) / total_mean,
        }

I_renew_energy = 20   # g/kWh, from ElectricityMap
I_fossil_energy = 740  # g/kWh, from ElectricityMap
Y_lifepace_ref = 4.0   # lifespan of typical server or satellite (years)


# ---- input variables for lifecycle CUE of terrestrial and orbital DCs ---------
Google_DC = terrestrialDC_paramaters['Google']
PUE = Google_DC['PUE_average']  # power usage effectiveness, same for all DC

constants = {
    'Es1_to_Es2': Google_DC['Es1_to_Es2_ratio_average'],                    # same for all DC; for the orbital DC this stands in for on-site fuel use of the operator's ground segment (ground stations, mission control, backup generators)
    'Es3_recurrent_to_Es2': Google_DC['Es3_recurrent_to_E2_ratio_average'],  # same for all DC, including the orbital DC: its ground segment (ground stations, mission control, operations staff) incurs the same class of recurring scope-3 (purchased goods/services, fuel- & energy-related, travel/commuting, waste), so Google's ratio is retained as a proxy
    'Es3_onetime_total_to_Es2_terrestrial': Google_DC['Es3_onetime_to_E2_ratio_average'] * Y_lifepace_ref,
    'I_s1': Google_DC['scope1_carbon_intensity_average'],                    # g/kWh, same for all DC
    'I_s3': scope3_carbon_intensity * 1000,                                  # g/kWh, same for all DC
    'I_s2_renewable_grid': I_renew_energy,                                   # g/kWh
    'I_s2_mixed_grid': Google_DC['scope2_carbon_intensity_average'],         # g/kWh
    'I_s2_dirty_grid': I_fossil_energy,                                      # g/kWh
    'I_s2_orbital': 0,                                                       # solar energy in space
}

variables = {}

# Orbital DC — one entry per launcher scenario.
# Scope-1 and recurring scope-3 are inherited from Google's terrestrial data
# centres as a proxy for the operator's *ground segment* (ground stations that
# communicate with the compute satellites, mission control and operations
# staff). That ground segment incurs the same kind of on-site fuel use
# (scope-1) and recurring scope-3 (purchased goods/services, fuel- &
# energy-related emissions, travel/commuting, waste) as a terrestrial DC.
# The space segment itself has no scope-1 or recurring scope-3 — its only large
# scope-3 item, the launcher, is captured in 'scope_3_ontime' below.
for sc in SCENARIOS:
    variables[f'Orbital_DC_{sc["name"]}'] = {
        'scope_1': {
            'E_to_Es2_ratio': constants['Es1_to_Es2'],
            'Intensity': constants['I_s1'],
        },
        'scope_2': {
            'E_to_Es2_ratio': 1,
            'Intensity': 0,
        },
        'scope_3_ontime': {
            'E_to_Es2_ratio': orbital_ratios[sc["name"]],
            'Intensity': constants['I_s3'],
        },
        'scope_3_recurrent': {
            'E_to_Es2_ratio': constants['Es3_recurrent_to_Es2'],
            'Intensity': constants['I_s3'],
        },
    }

# Terrestrial DCs — three grid-carbon-intensity cases
terrestrial_scope = {
    'scope_1': {
        'E_to_Es2_ratio': constants['Es1_to_Es2'],
        'Intensity': constants['I_s1'],
    },
    'scope_3_ontime': {
        'E_to_Es2_ratio': constants['Es3_onetime_total_to_Es2_terrestrial'],
        'Intensity': constants['I_s3'],
    },
    'scope_3_recurrent': {
        'E_to_Es2_ratio': constants['Es3_recurrent_to_Es2'],
        'Intensity': constants['I_s3'],
    },
}
for grid_name, grid_intensity in [
    ('Terrestrial_DC_renewable_grid', constants['I_s2_renewable_grid']),
    ('Terrestrial_DC_mixed_grid', constants['I_s2_mixed_grid']),
    ('Terrestrial_DC_dirty_grid', constants['I_s2_dirty_grid']),
]:
    variables[grid_name] = {
        'scope_1': dict(terrestrial_scope['scope_1']),
        'scope_2': {'E_to_Es2_ratio': 1, 'Intensity': grid_intensity},
        'scope_3_ontime': dict(terrestrial_scope['scope_3_ontime']),
        'scope_3_recurrent': dict(terrestrial_scope['scope_3_recurrent']),
    }


# ---- evaluate lifecycle CUE (equation #3 in the paper) -----------------------
lifespan = np.arange(1, 20.1, step=0.1)
CUE = {}

for key1, item1 in variables.items():
    CUE_temp = 0
    for key2, item2 in item1.items():
        k = lifespan if key2 == 'scope_3_ontime' else 1
        Esi_Es2_ratio = item2['E_to_Es2_ratio']
        Isi = item2['Intensity']
        EI_i = Esi_Es2_ratio * Isi / k
        CUE_temp += PUE * EI_i
    CUE[key1] = np.round(CUE_temp, 0)


# ---- plot Lifecycle CUE ------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "mathtext.fontset": "custom",
    "mathtext.it": "Arial:italic",
    "axes.titlesize": 30,
    "axes.labelsize": 14,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
})

figure = plt.figure()

# Orbital scenario curves (solid, per-scenario colour)
for sc in SCENARIOS:
    key = f'Orbital_DC_{sc["name"]}'
    plt.plot(lifespan, CUE[key] / 1000, color=sc["color"],
             alpha=0.8, linewidth=3, label=sc["label"])

# Falcon 9 EI(BC) 10-30 g/kg grey band (scope-3 onetime launch term only)
if falcon9_band is not None:
    _key = 'Orbital_DC_falcon9'
    _dCUE = PUE * (falcon9_band["delta_ratio"] * constants['I_s3'] / lifespan)  # g/kWh
    plt.fill_between(lifespan,
                     (CUE[_key] - _dCUE) / 1000,
                     (CUE[_key] + _dCUE) / 1000,
                     color="grey", alpha=0.25, linewidth=0)

# Terrestrial curves (dashed), in legend order: renewable, mixed, dirty
plt.plot(lifespan, CUE['Terrestrial_DC_renewable_grid'] / 1000, '--', linewidth=2, alpha=1)
plt.plot(lifespan, CUE['Terrestrial_DC_mixed_grid'] / 1000, '--', linewidth=2, alpha=1)
plt.plot(lifespan, CUE['Terrestrial_DC_dirty_grid'] / 1000, '--', color='r', linewidth=2, alpha=1)

# Google data-centre reference point at 4 years
Liftime_CUE_Google = Google_DC['Lifecycle_CUE'] / 1000
plt.plot(Y_lifepace_ref, Liftime_CUE_Google, '*', color='tab:orange',
         markersize=10, alpha=1, label='Google')
plt.vlines(Y_lifepace_ref, 0, Liftime_CUE_Google, color='dimgrey',
           alpha=0.4, linestyle='--', linewidth=1)

Legends = [sc["label"] for sc in SCENARIOS] + [
    'Terrestrial DC: renewable grid',
    'Terrestrial DC: mixed grid',
    'Terrestrial DC: dirty grid',
    'Google DC',
]
_handles = list(plt.gca().get_lines())
if falcon9_band is not None:
    # slot the band entry immediately after the Falcon 9 curve
    _idx = next(i for i, lab in enumerate(Legends) if "Falcon" in lab)
    _handles.insert(_idx + 1, Patch(facecolor="grey", alpha=0.25))
    Legends.insert(_idx + 1, "Launcher BC EI range: 10\u201330 g/kg")
plt.legend(_handles, Legends, loc=[0.25, 0.5], frameon=False, fontsize=13)

plt.text(0.45, 0.38, 
         f"Evaltued with Aviation CFs. \nPower density: {cppk:.0f} W/kg",
         transform=plt.gca().transAxes, 
         family="Arial", 
        #  weight="bold", 
         fontsize=13,)

plt.gca().spines[['right', 'top']].set_visible(False)
plt.gca().spines[['left', 'bottom']].set_linewidth(1.5)
plt.gca().spines['left'].set_position(('data', 0.5))
plt.gca().spines['bottom'].set_position(('data', 0.4))

# Xaxis_range = [0.3, 15.5]
# Yaxis_range = [0.32, 1.99 * 2]
Xaxis_range = [0.3, 15]
Yaxis_range = [0.32, 2* 2]
plt.xlim(Xaxis_range)
plt.ylim(Yaxis_range)

# plt.xticks(np.arange(1, 14.9, step=1), weight='bold', rotation=0)
# plt.yticks(np.arange(0.5, 1.9 * 2, step=0.5), weight='bold', rotation=0)
plt.xticks(np.arange(1, 15.1, step=1), weight='bold', rotation=0)
plt.yticks(np.arange(0.5, 4.1, step=0.5), weight='bold', rotation=0)
plt.gca().yaxis.set_minor_locator(AutoMinorLocator(2))

plt.gca().set_position([0.13, 0.1, 0.8, 0.75])
# plt.gca().arrow(14.95, 0.4, 0.55, 0, length_includes_head=True, width=0.0,
#                head_width=0.1, shape='full', head_length=0.4, edgecolor='k', facecolor='k')
# plt.gca().arrow(0.5, 1.97 * 2, 0, 0.052, length_includes_head=True, width=0.0,
#                head_width=0.3, shape='full', head_length=0.2, edgecolor='k', facecolor='k')
plt.gca().patch.set_alpha(0.0)

plt.xlabel('Lifespan of satellite or server (years)', family='Arial', weight='bold')
plt.ylabel('Lifecycle CUE ($kgCO_{2}\,eq\,/\,kWh$)', family='Arial', weight='bold')

# plt.savefig(script_dir/'Path2_lifecycle_CUE_vs_lifespan.pdf', format='pdf', dpi=1000, bbox_inches='tight')
plt.savefig(script_dir/'Path2_lifecycle_CUE_vs_lifespan.svg', format='svg', dpi=1000, bbox_inches='tight')

plt.show()

for sc in SCENARIOS:
    print(f"ratio [{sc['name']}]: {orbital_ratios[sc['name']]}")
