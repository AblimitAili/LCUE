# orbital-vs-terrestrial-datacentre-lcue

Analysis code and data reproducing the launcher lifecycle GWP100 emission
modelling and the lifecycle carbon-usage-effectiveness (L-CUE) re-analysis of
orbital data centres versus terrestrial data centres, presented in the
Addendum to:

> Aili, A.; Choi, J.; Ong, Y. S.; Wen, Y. *The development of carbon-neutral
> data centres in space.* **Nature Electronics** (2025).
> DOI: 10.1038/s41928-025-01476-1

---

## Overview

This repository contains three self-contained analysis folders that share one
parent directory:

| Folder | Purpose |
|---|---|
| `hydrocarbon_launcher_lifecycle_GWP100_analysis/` | Launch-phase + all-phase GWP100 model for **methane (LNG)** and **kerosene** engines (Falcon 9, Merlin 1D), incl. the black-carbon emission-index band. |
| `hydrogen_launcher_lifecycle_GWP100_analysis/` | Launch-phase + all-phase GWP100 model for the **hydrogen** engine (LH₂), with validation against Calabuig et al. |
| `orbital_DC_vs_terrestrial_DC_analysis/` | Orbital-vs-terrestrial **L-CUE** comparison (Figures 1A/1B of the Addendum), power-density break-even analysis, and decarbonisation scenarios. |

> **Important:** the orbital folder resolves the other two folders via
> `Path(__file__).parent.parent` in `s0_scenarios.py`. **Keep the three folders
> as siblings** — do not rename or move them relative to each other (unless you
> also update `HYDROCARBON_DIR` / `HYDROGEN_DIR` in `s0_scenarios.py`).

## Dependencies

- Python 3.9+
- `numpy` and `matplotlib` (see `requirements.txt`); all other imports are
  standard library.

```bash
pip install -r requirements.txt
```

For exact reproducibility, freeze the resolved versions after installing:
`pip freeze > requirements.lock`.

## How to run

Run the folders **in order**, because each stage consumes the JSON outputs of
the previous one, and the orbital analysis consumes the two launcher folders'
outputs.

### 1. Hydrocarbon (methane + kerosene)

```bash
cd hydrocarbon_launcher_lifecycle_GWP100_analysis
python s1_launch_phase_GWP100_methane_and_kersene.py   # launch model + BC EI sweep
python s2_validate_launch_phase.py                     # cross-check vs Calabuig et al.
python s3_all_phases_GWP100_methane.py                 # methane all-phases (aviation + high-alt)
python s4_all_phases_GWP100_kerosene.py                # kerosene all-phases + Falcon 9 bc_band
cd ..
```

### 2. Hydrogen

```bash
cd hydrogen_launcher_lifecycle_GWP100_analysis
python run_all_hydrogen.py   # s1 -> s2 -> s3 (incl. validation)
cd ..
```

### 3. Orbital-vs-terrestrial L-CUE

```bash
cd orbital_DC_vs_terrestrial_DC_analysis
python s0b_decarbonization.py        # (helper) decarbonisation percentages
python run_all_s0_s3.py              # s1 -> s2_Orbital -> s2_Google -> s3  (Figure 1A)
python s4_power_density.py     # power-density break-even               (Figure 1B)
cd ..
```

`run_all_s0_s3.py` executes the steps in dependency order and halts on failure.

### Minimal re-run (after editing launch/BC inputs)

```bash
python hydrocarbon_launcher_lifecycle_GWP100_analysis/s1_launch_phase_GWP100_methane_and_kersene.py
python hydrocarbon_launcher_lifecycle_GWP100_analysis/s4_all_phases_GWP100_kerosene.py
python orbital_DC_vs_terrestrial_DC_analysis/s3_LCUE_Terrestrial_vs_Orbital.py
python orbital_DC_vs_terrestrial_DC_analysis/s4_power_density.py
```

## Key outputs

| Output | File |
|---|---|
| Figure 1A — L-CUE vs lifespan, aviation CFs (with/without decarbonisation) | `orbital_DC_vs_terrestrial_DC_analysis/Path2_lifecycle_CUE_vs_lifespan.svg` |
| Figure 1B — L-CUE vs lifespan, high-altitude CFs, raised power density | `orbital_DC_vs_terrestrial_DC_analysis/Path3_power_density_break_even.svg` |
| Scope-3 onetime pie charts (Figure 1A insets) | `orbital_DC_vs_terrestrial_DC_analysis/Scope3_Onetime_Emissions_PieChart_*.svg` |
| Required power-density table (Figure 1B inset) | `orbital_DC_vs_terrestrial_DC_analysis/Required_power_density_table.csv/.json` |
| Falcon 9 launch + all-phase GWP100 (incl. `bc_band`) | `hydrocarbon_.../falcon9_phase_gwp100_aviation.json`, `..._highalt.json` |
| Hydrogen launcher all-phase GWP100 | `hydrogen_.../phases_gwp100_hydrogen_launchers_{aviation,highalt}.json` |

## Model conventions

- **Two CF scenarios** per engine: aviation-only vs aviation + high-altitude
  characterisation factors (GWP100).
- **Altitude split**: 58.9% of propellant burns in the stratosphere, 41.1% in
  the troposphere; post-combustion black-carbon survival 75.4% (stratosphere)
  vs ~4% (troposphere).
- **Black-carbon emission-index band**: EI(BC) swept over 10–30 g/kg
  (kerosene centre 20 g/kg), shown as a grey uncertainty band on Figures 1A/1B.
- **High-altitude CF reproduction factors**: BC × 0.90 and H₂O × 0.79 are
  applied to force-match the published high-altitude GWP100 values (see
  `hydrogen_.../s1_launch_phase_GWP100_hydrogen.py` comments).
- **Decarbonisation scenario**: all ground phases except Launch and Re-entry are
  decarbonised by 72% (see `s0_scenarios.py`, `s0b_decarbonization.py`).

## License & citation

This code is provided under the MIT license (see `LICENSE`). If you use it,
please cite:

```bibtex
@article{aili2025orbital,
  title   = {The development of carbon-neutral data centres in space},
  author  = {Aili, Ablimit and Choi, Jihwan and Ong, Yew Soon and Wen, Yonggang},
  journal = {Nature Electronics},
  year    = {2025},
  doi     = {10.1038/s41928-025-01476-1}
}
```

Repository: https://github.com/<user>/LUCE
