"""
Run the hydrogen (LH2 VTVL) fleet launch-phase + all-phases pipeline end-to-end.

Sequence (each step depends on the previous one's JSON output):
    1. s1_launch_phase_GWP100_hydrogen.py      -> launch_gwp100_species_hydrogen.json
                                                   effective_emission_indices_hydrogen.json
    2. s2_all_phases_GWP100_hydrogen.py        -> phases_gwp100_hydrogen_launchers_aviation.json
                                                   phases_gwp100_hydrogen_launchers_highalt.json
    3. s3_validate_launch_phase_hydrogen.py    -> console cross-check vs Table 5 / Table 6

No external inputs are required beyond the three scripts themselves (all paper
values - Tables 1/2/4/5/6, Fig. 5 - are encoded in the scripts).

Notes:
  - s2 reads the launch model output (launch_gwp100_species_hydrogen.json)
    written by s1, so s1 MUST run first.
  - The high-altitude fleet total is NOT force-matched to CC*; the validator
    reports the ~19% H2O-CF-uncertainty overshoot rather than asserting equality.
"""

import subprocess
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent

STEPS = [
    ("s1_launch_phase_GWP100_hydrogen.py", "Launch-event emission model (Prometheus-H + SLME)"),
    ("s2_all_phases_GWP100_hydrogen.py", "Per-launcher phase breakdown (aviation + high-alt)"),
    ("s3_validate_launch_phase_hydrogen.py", "Cross-check vs Table 5 / Table 6"),
]


def main():
    for script, desc in STEPS:
        print(f"\n=== [{script}] {desc} ===")
        result = subprocess.run([sys.executable, script], cwd=str(script_dir))
        if result.returncode != 0:
            print(f"\nFAILED at {script} (exit {result.returncode}). Halting.")
            sys.exit(result.returncode)
    print("\nPipeline complete.")
    print("Outputs:")
    print("  launch_gwp100_species_hydrogen.json")
    print("  effective_emission_indices_hydrogen.json")
    print("  phases_gwp100_hydrogen_launchers_aviation.json")
    print("  phases_gwp100_hydrogen_launchers_highalt.json")


if __name__ == "__main__":
    main()
