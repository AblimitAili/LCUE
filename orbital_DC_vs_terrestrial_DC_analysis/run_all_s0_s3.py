"""
Run the orbital-vs-terrestrial Lifecycle CUE pipeline end-to-end.

Sequence (each step depends on the previous one's JSON output):
    1. s1_component_parameters.py                  -> Orbital_DC_emissions_<name>.json
    2. s2_Orbital_DC_emissions_reanalysis.py       -> Orbital_DC_emissions_reanalysis_<name>.json
    3. s2_Google_DC_emissions_reanalysis.py        -> Google_DC_emissions_reanalysis.json
    4. s3_LCUE_Terrestrial_vs_Orbital.py           -> Lifecycle_CUE_vs_lifespan.pdf/.svg

`scenarios.json` is the config read by s1 / s2_Orbital / s3 (not executed).
Requires `Google_DC_emisssions.json` (raw terrestrial input) to already exist.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

STEPS = [
    ("s1_component_parameters.py", "Compute orbital DC + launch emissions"),
    ("s2_Orbital_DC_emissions_reanalysis.py", "Reanalyse orbital scenarios"),
    ("s2_Google_DC_emissions_reanalysis.py", "Reanalyse terrestrial Google DC"),
    ("s3_LCUE_Terrestrial_vs_Orbital.py", "Plot L-CUE comparison"),
]


def main():
    for script, desc in STEPS:
        print(f"\n=== [{script}] {desc} ===")
        result = subprocess.run([sys.executable, script], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nFAILED at {script} (exit {result.returncode}). Halting.")
            sys.exit(result.returncode)
    print("\nPipeline complete.")
    print("Outputs: Orbital_DC_emissions_reanalysis_*.json, "
          "Google_DC_emissions_reanalysis.json, Lifecycle_CUE_vs_lifespan.pdf/.svg")


if __name__ == "__main__":
    main()
