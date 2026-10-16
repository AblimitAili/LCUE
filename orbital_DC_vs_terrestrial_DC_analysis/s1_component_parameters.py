"""
s1 — Compute the orbital data centre scope-3 onetime energy/emissions for each
launcher scenario defined in `scenarios.json`.

Key change vs. the original: the launch footprint is now expressed as
`emission_per_launch_kg` (total scope-3 launch GWP100 per launch, aviation CFs)
instead of a per-kg-of-propellant factor, and `num_launches` is computed from the
fleet mass and the scenario payload.
"""

import json
import math
from pathlib import Path

script_dir = Path(__file__).resolve().parent

# with open("scenarios.json") as _f:
#     SCENARIOS = json.load(_f)["scenarios"]
from s0_scenarios import SCENARIOS
SCENARIOS = [s for s in SCENARIOS if s.get("enabled", True)]

# ---- Fixed (non-launcher) orbital-DC parameters ------------------------------
CARRIER_SAT_MASS = 260.0          # kg
NUM_SATELLITES = 4425             # -
SOLAR_PANEL_AREA = 30.0           # m2
PANEL_EFFICIENCY = 0.17           # -
SUN_EXPOSURE = 1.0                # -
SOLAR_INTENSITY = 1366.0          # W/m2
SERVER_MASS = 28.6                # kg
SERVER_MAX_POWER = 510.0          # W
SERVER_MANUF_ENERGY = 3583.0      # kWh
CARBON_INTENSITY = 0.271          # kg CO2eq / kWh (scope-3)
COMPUTE_FRACTION = 0.5            # -
PUE = 1.1                         # -
RADIATOR_MASS = 35.0/2              # kg; devided by because both surfaces of the radiator provides cooling. 
RADIATOR_CARBON_INTENSITY = 17.0  # kg CO2eq / kg


def calculate_servers(solar_panel_area, solar_intensity, panel_efficiency,
                      sun_exposure, compute_fraction, server_max_power):
    total_power = solar_panel_area * solar_intensity * panel_efficiency * sun_exposure
    computing_power = total_power * compute_fraction
    servers = computing_power / server_max_power
    return {
        "total_solar_power_W": round(total_power, 2),
        "sever_comppute_power_W": round(computing_power, 2),
        "servers": round(servers, 3),
        "servers_actual": int(servers),
    }


def compute_orbital_dc(payload_kg, emission_per_launch_kg):
    """Return (output_dict, num_launches) for one launcher scenario."""
    server_emissions_per_server = SERVER_MANUF_ENERGY * CARBON_INTENSITY
    radiator_emissions_per_server = RADIATOR_MASS * RADIATOR_CARBON_INTENSITY

    server_power_params = calculate_servers(
        SOLAR_PANEL_AREA, SOLAR_INTENSITY, PANEL_EFFICIENCY,
        SUN_EXPOSURE, COMPUTE_FRACTION, SERVER_MAX_POWER)
    num_servers = server_power_params['servers_actual']

    satellite_manuf_emissions = (CARRIER_SAT_MASS / SERVER_MASS) * server_emissions_per_server
    satellite_mass = CARRIER_SAT_MASS + num_servers * (SERVER_MASS + RADIATOR_MASS)
    total_mass_all = satellite_mass * NUM_SATELLITES

    total_solar_power_W = server_power_params['total_solar_power_W'] 
    power_per_kg = total_solar_power_W /satellite_mass

    num_launches = math.ceil(total_mass_all / payload_kg)

    print(f"{num_launches=}")

    total_launch_emissions = num_launches * emission_per_launch_kg
    launch_emissions_per_satellite = total_launch_emissions / NUM_SATELLITES

    total_scope3_emissions = (
        num_servers * server_emissions_per_server
        + num_servers * radiator_emissions_per_server
        + satellite_manuf_emissions
        + launch_emissions_per_satellite
    )

    # Convert the scope-3 onetime emissions to equivalent energy (kWh) via the
    # scope-3 carbon intensity, keeping the paper's energy-based methodology.
    radiator_energy_per_server = radiator_emissions_per_server / CARBON_INTENSITY
    satellite_manuf_energy = satellite_manuf_emissions / CARBON_INTENSITY
    launch_energy_per_satellite = launch_emissions_per_satellite / CARBON_INTENSITY
    total_scope3_energy = (
        num_servers * SERVER_MANUF_ENERGY
        + num_servers * radiator_energy_per_server
        + satellite_manuf_energy
        + launch_energy_per_satellite
    )

    solar_power_generated_W = server_power_params['total_solar_power_W']
    Es2 = (24 * 365 / 1000 * solar_power_generated_W)
    Es3_onetime_to_Es2 = total_scope3_energy / Es2

    output = {
        "Orbital_DC_StarlinkBased": {
            "N_servers_perSat": num_servers,
            "PUE": PUE,
            "scope2_carbon_intensity": 0,
            "scope3_carbon_intensity": round(CARBON_INTENSITY, 3),
            "Es2_energy": round(Es2, 1),
            "satellite_mass_kg": round(satellite_mass, 1),
            "total_solar_power_W": round(total_solar_power_W,1),
            "power_per_kg_in_W_kg": round(power_per_kg, 0),
            "Es3_onetime_energy": {
                "capital_server": round(num_servers * (SERVER_MANUF_ENERGY + radiator_energy_per_server), 1),
                "capital_satellite": round(satellite_manuf_energy, 1),
                "upstream_transport": round(launch_energy_per_satellite, 1),
            },
        }
    }
    return output, num_launches


if __name__ == '__main__':
    for sc in SCENARIOS:
        output, num_launches = compute_orbital_dc(sc["payload_kg"], sc["emission_per_launch_kg"])
        with open(script_dir/f'Orbital_DC_emissions_{sc["name"]}.json', 'w', encoding="utf-8") as f:
            json.dump(output, f, indent=4)
        print(f'{sc["name"]:15s} {sc["label"]:28s} -> {num_launches} launches')
