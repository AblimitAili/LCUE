"""
s4 — Path 2: power density (W/kg) as the lever for orbital-DC competitiveness.

Finds the break-even power density at t = 4 yr where
    L-CUE_orbital(4) = L-CUE_terrestrial(4, mixed grid),
for each launcher, under two CF scenarios (aviation / high-altitude).

Launch GWP100 per launch is read from the upstream LCA JSONs (no hardcoding):
    Falcon 9 (RP-1/LOX)   and   LH2 XXL-RLV.
"""
import json
import csv
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator
from pathlib import Path

script_dir = Path(__file__).resolve().parent
ROOT = script_dir.parent
HC = ROOT / "hydrocarbon_launcher_lifecycle_GWP100_analysis"
HY = ROOT / "hydrogen_launcher_lifecycle_GWP100_analysis"


def _gwp_kg(folder, json_name, key):
    """Read per-launch GWP100 [Gg] from an upstream LCA JSON -> kg/launch.

    key:  str   -> top-level field,  e.g. "total_per_launch_Gg" (Falcon 9)
          tuple -> nested path,      e.g. ("per_launcher_sum_Gg", "XXL-RLV")
    """
    with open(folder / json_name, encoding="utf-8") as f:
        data = json.load(f)
    for part in (key,) if isinstance(key, str) else key:
        data = data[part]
    return data * 1e6   # Gg -> kg


# ---- launcher cases ---------------------------------------------------------
CASES = [
    {
        "name": "falcon9",
        "label": "Falcon 9 (Kerosene)",
        "fuel": "RP-1/LOX",
        "color": "black",
        "s1_json": "Orbital_DC_emissions_falcon9.json",
        "gwp_av": _gwp_kg(HC, "falcon9_phase_gwp100_aviation.json",
                          "total_per_launch_Gg"),
        "gwp_hi": _gwp_kg(HC, "falcon9_phase_gwp100_highalt.json",
                          "total_per_launch_Gg"),
    },
    {
        "name": "h2_xxlrlv_exp",
        "label": "XXL-RLV (exp. core, LH2)",
        "fuel": "LH2",
        "color": "red",
        "s1_json": "Orbital_DC_emissions_h2_xxlrlv_exp.json",
        "gwp_av": _gwp_kg(HY, "phases_gwp100_hydrogen_launchers_aviation.json",
                        ("per_launcher_sum_Gg", "XXL-RLV exp. core")),
        "gwp_hi": _gwp_kg(HY, "phases_gwp100_hydrogen_launchers_highalt.json",
                        ("per_launcher_sum_highalt_Gg", "XXL-RLV exp. core")),
    },
    {
        "name": "ch4_xxl_exp",
        "label": "LCH4 XXL-RLV exp. core",
        "fuel": "LCH4",
        "color": "blue",
        "s1_json": "Orbital_DC_emissions_xxl_exp.json",
        "gwp_av": _gwp_kg(HC, "phases_gwp100_methane_launchers_aviation.json",
                        ("per_launcher_sum_Gg", "XXL-exp")),
        "gwp_hi": _gwp_kg(HC, "phases_gwp100_methane_launchers_highalt.json",
                        ("per_launcher_sum_highalt_Gg", "XXL-exp")),
    },
]

# ---- base orbital-DC design params (launcher-independent) --------------------
with open(script_dir / "Orbital_DC_emissions_falcon9.json", encoding="utf-8") as f:
    s1 = json.load(f)["Orbital_DC_StarlinkBased"]

Es2 = s1["Es2_energy"]                                              # kWh/yr / sat
capital = (s1["Es3_onetime_energy"]["capital_server"]
           + s1["Es3_onetime_energy"]["capital_satellite"])         # kWh
P_total = s1["total_solar_power_W"]                                 # W
mass0 = s1["satellite_mass_kg"]                                     # kg
Wkg0 = P_total / mass0                                              # current W/kg

# ---- terrestrial (mixed grid) ----------------------------------------------
with open(script_dir / "Google_DC_emissions_reanalysis.json", encoding="utf-8") as f:
    g = json.load(f)["Google"]

PUE = g["PUE_average"]
E1r = g["Es1_to_Es2_ratio_average"]
E3r = g["Es3_recurrent_to_E2_ratio_average"]
E3o_avg = g["Es3_onetime_to_E2_ratio_average"]                      # annualised
I_s1 = g["scope1_carbon_intensity_average"]                         # g/kWh
I_s2_mixed = g["scope2_carbon_intensity_average"]                   # g/kWh
I_s3 = s1["scope3_carbon_intensity"] * 1000                         # g/kWh

# ---- L-CUE functions --------------------------------------------------------
def cue_orbital(t, Wkg, launch0, launch_scale):
    launch = launch0 * launch_scale * (Wkg0 / Wkg)
    E3o_ratio = (capital + launch) / Es2
    return PUE * (E1r * I_s1 + E3o_ratio * I_s3 / t + E3r * I_s3)


def cue_terrestrial(t):
    return PUE * (E1r * I_s1 + I_s2_mixed + E3o_avg * 4 * I_s3 / t + E3r * I_s3)


def break_even_Wkg(launch0, launch_scale):
    target = cue_terrestrial(4.0)
    lo, hi = Wkg0, Wkg0 * 1e6
    for _ in range(200):
        mid = (lo + hi) / 2
        if cue_orbital(4.0, mid, launch0, launch_scale) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# ---- evaluate each case -----------------------------------------------------
print("Launch GWP100 (kg CO2eq/launch):")
for c in CASES:
    with open(script_dir / c["s1_json"], encoding="utf-8") as f:
        s1c = json.load(f)["Orbital_DC_StarlinkBased"]
    c["launch0"] = s1c["Es3_onetime_energy"]["upstream_transport"]   # kWh (aviation)
    c["scale_hi"] = c["gwp_hi"] / c["gwp_av"]
    c["scale_hi_band"] = None
    if c["name"] == "falcon9":
        # EI(BC) 10-30 g/kg band (high-alt CFs): the launch term is linear in
        # the per-launch GWP, so scale the aviation launch by each band member.
        with open(HC / "falcon9_phase_gwp100_highalt.json", encoding="utf-8") as f:
            _hi_band_Gg = json.load(f)["bc_band"]["total_per_launch_Gg"]
        c["scale_hi_band"] = [v * 1e6 / c["gwp_av"] for v in _hi_band_Gg]
    c["Wkg_av"] = break_even_Wkg(c["launch0"], 1.0)
    c["Wkg_hi"] = break_even_Wkg(c["launch0"], c["scale_hi"])

    print(f"  {c['label']:16s} av {c['gwp_av']:12.0f}  hi {c['gwp_hi']:14.0f}  ratio {c['scale_hi']:7.1f}")
    print(f"  {c['label']:16s} current {Wkg0:.1f} W/kg | "
          f"break-even av {c['Wkg_av']:8.1f} W/kg (x{c['Wkg_av']/Wkg0:.1f}) | "
          f"break-even hi {c['Wkg_hi']:8.1f} W/kg (x{c['Wkg_hi']/Wkg0:.1f})")

# ---- table: required power density to break even at t = 4 yr ----------------
_header = ["Launcher", "Fuel", "Launch GWP av (Gg)", "Launch GWP high-alt (Gg)",
           "Req. power density av (W/kg)", "Req. power density high-alt (W/kg)",
           "vs current av (x)", "vs current high-alt (x)"]
_rows = []
for c in CASES:
    _rows.append([
        c["label"],
        c["fuel"],
        f"{c['gwp_av'] / 1e6:.3f}",
        f"{c['gwp_hi'] / 1e6:.2f}",
        f"{c['Wkg_av']:.1f}",
        f"{c['Wkg_hi']:.1f}",
        f"{c['Wkg_av'] / Wkg0:.2f}",
        f"{c['Wkg_hi'] / Wkg0:.1f}",
    ])

_widths = []
for i, h in enumerate(_header):
    _widths.append(max([len(h)] + [len(r[i]) for r in _rows]))


def _fmt_row(cells):
    return "  ".join(cell.ljust(_widths[i]) for i, cell in enumerate(cells))


print(f"\nRequired power density to break even at t = 4 yr (current = {Wkg0:.1f} W/kg):")
print(_fmt_row(_header))
print("  ".join("-" * w for w in _widths))
for r in _rows:
    print(_fmt_row(r))

with open(script_dir / "Required_power_density_table.csv",
          "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(_header)
    w.writerows(_rows)
print("\nWrote Required_power_density_table.csv (also printed above).")

# JSON version of the power-density table (for downstream use)
_json_table = {
    "current_power_density_W_per_kg": round(Wkg0, 3),
    "break_even_lifespan_years": 4.0,
    "launchers": [
        {
            "name": c["name"],
            "label": c["label"],
            "fuel": c["fuel"],
            "launch_gwp_av_Gg": round(c["gwp_av"] / 1e6, 3),
            "launch_gwp_highalt_Gg": round(c["gwp_hi"] / 1e6, 3),
            "required_power_density_av_W_per_kg": round(c["Wkg_av"], 3),
            "required_power_density_highalt_W_per_kg": round(c["Wkg_hi"], 3),
        }
        for c in CASES
    ],
}
with open(script_dir / "Required_power_density_table.json",
          "w", encoding="utf-8") as f:
    json.dump(_json_table, f, indent=4)
print("Wrote Required_power_density_table.json.")


# ---- plot (log Y) -----------------------------------------------------------
lifespan = np.arange(1, 20.1, step=0.1)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "mathtext.fontset": "custom",
    "mathtext.it": "Arial:italic",
    "axes.titlesize": 30, "axes.labelsize": 14,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 14,
})

# ---- layout knobs (axes-fraction coords; tweak freely) ----------------------
FIG_SIZE = (7, 7.5)              # (width, height) in inches

TOP_LEGEND_LOC    = (0.25, 0.7)      # upper-panel legend anchor point (x, y)
TOP_LEGEND_ANCHOR = 'lower left'  # corner of the legend box placed at TOP_LEGEND_LOC

TEXTBOX_LOC = (0.5, 0.45)         # "current power density" box, top-right corner
TEXTBOX_TITLE       = "Evaluated with High-altitude CFs"   # line 1 of the box
TEXTBOX_POWER       = True          # show "Power density: <W/kg>" as line 2
TEXTBOX_FONTSIZE    = 13
TEXTBOX_HA          = 'left'        # horizontal alignment of the text block
TEXTBOX_VA          = 'top'         # vertical alignment of the text block
TEXTBOX_LINESPACING = 1.4
TEXTBOX_ALPHA       = 0.0           # background box opacity

BOT_LEGEND_LOC = (0.3, 0.00)       # lower-panel legend anchor point (x, y)
BOT_LEGEND_ANCHOR = 'lower left'   # corner of the legend box placed at BOT_LEGEND_LOC
TABLE_LOC = (0.98, 0.88)           # lower-panel table, top-right corner

figure = plt.figure(figsize=FIG_SIZE)
gs = figure.add_gridspec(2, 1, height_ratios=[0.8, 1.0], hspace=0.05,
                         left=0.14, right=0.98, top=0.94, bottom=0.12)
ax_top = figure.add_subplot(gs[0])
ax_bot = figure.add_subplot(gs[1], sharex=ax_top)

_c0 = CASES[0]
_y_break = cue_terrestrial(4.0) / 1000   # kg CO2eq/kWh at break-even

# ---- upper panel: orbital DC @ CURRENT power density, high-alt CFs ----------
for c in CASES:
    if c["name"] == "ch4_xxl_exp":
        continue  # methane high-alt ≈ kerosene (both hydrocarbon) — dropped
    ax_top.plot(lifespan,
                cue_orbital(lifespan, Wkg0, c["launch0"], c["scale_hi"]) / 1000,
                color=c["color"], linewidth=2.5, linestyle='-',
                label=f'Orbital DC — {c["label"]}')

# Falcon 9 EI(BC) 10-30 g/kg grey band (high-alt CFs)
_f9 = next(c for c in CASES if c["name"] == "falcon9")
if _f9.get("scale_hi_band"):
    _lo = cue_orbital(lifespan, Wkg0, _f9["launch0"], _f9["scale_hi_band"][0]) / 1000
    _hi = cue_orbital(lifespan, Wkg0, _f9["launch0"], _f9["scale_hi_band"][2]) / 1000
    ax_top.fill_between(lifespan, _lo, _hi, color="grey", alpha=0.25, linewidth=0)

ax_top.set_yscale('log')
ax_top.set_ylim(10, 4000)
ax_top.set_yticks([10, 100, 1000, 4000])
ax_top.set_yticklabels(['10', '100', '1000', '4000'], weight='bold')
ax_top.yaxis.set_minor_locator(AutoMinorLocator(2))
_handles, _labels = ax_top.get_legend_handles_labels()
if _f9.get("scale_hi_band"):
    # slot the band entry immediately after the Falcon 9 curve
    _idx = next(i for i, lab in enumerate(_labels) if "Falcon 9" in lab)
    _handles.insert(_idx + 1, Patch(facecolor="grey", alpha=0.25))
    # _labels.insert(_idx + 1, "Falcon 9 (EI(BC) 10\u201330 g/kg)")
    _labels.insert(_idx + 1, "BC emission index range: 10\u201330 g/kg")
ax_top.legend(_handles, _labels, frameon=False, fontsize=14,
               bbox_to_anchor=TOP_LEGEND_LOC, loc=TOP_LEGEND_ANCHOR)
_text_lines = [TEXTBOX_TITLE]
if TEXTBOX_POWER:
    _text_lines.append(f'Power density: {Wkg0:.0f} W/kg')
ax_top.text(*TEXTBOX_LOC,
            "\n".join(_text_lines),
            transform=ax_top.transAxes, va=TEXTBOX_VA, ha=TEXTBOX_HA,
            fontsize=TEXTBOX_FONTSIZE, linespacing=TEXTBOX_LINESPACING,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                      edgecolor='none', alpha=TEXTBOX_ALPHA))

# ---- lower panel: break-even + terrestrial ----------------------------------
ax_bot.plot(lifespan, cue_terrestrial(lifespan) / 1000,
            '--', color='tab:orange', linewidth=2, alpha=1,
            label='Terrestrial (mixed grid)')
ax_bot.plot(lifespan,
            cue_orbital(lifespan, _c0["Wkg_av"], _c0["launch0"], 1.0) / 1000,
            color='tab:blue', linewidth=3, alpha=1,
            label='Orbital DC (parity at year 4)')

# vertical dashed line + marker at the break-even point (year 4)
ax_bot.plot([4.0, 4.0], [_y_break, 0.3], linestyle='--', color='gray',
            linewidth=1.3, alpha=0.9, zorder=2)
ax_bot.plot(4.0, _y_break, 'o', color='gray', markersize=6, zorder=3)

ax_bot.set_yscale('log')
ax_bot.set_ylim(0.3, 10.1)
ax_bot.set_yticks([0.3, 0.5, 1, 2, 5])
ax_bot.set_yticklabels(['0.3', '0.5', '1', '2', '5'], weight='bold')
ax_bot.yaxis.set_minor_locator(AutoMinorLocator(2))
ax_bot.legend(frameon=False, fontsize=14,
               bbox_to_anchor=BOT_LEGEND_LOC, loc=BOT_LEGEND_ANCHOR)

# annotation table: required power density per launcher (upper-right, lower panel)
# _table_lines = ["Required power density (W/kg)"]
# _table_lines.append(f"{'Launcher':<24}{'av':>8}{'high-alt':>10}")
# for c in CASES:
#     _table_lines.append(
#         f"{c['label']:<24}{c['Wkg_av']:>8.1f}{c['Wkg_hi']:>10.0f}")
# _table_text = "\n".join(_table_lines)
# ax_bot.text(*TABLE_LOC, _table_text, transform=ax_bot.transAxes,
#             fontsize=13, family='monospace', va='top', ha='right',
#             linespacing=1.4)

# ---- shared spines, x-axis, break markers -----------------------------------
for ax in (ax_top, ax_bot):
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.set_xlim(0.2, 15.1)

ax_top.spines['bottom'].set_visible(False)
ax_top.spines['top'].set_visible(False)
ax_bot.spines['top'].set_visible(False)
ax_bot.spines['bottom'].set_linewidth(1.5)
ax_top.tick_params(bottom=False, labelbottom=False)

ax_bot.set_xticks(np.arange(1, 15, step=1))
ax_bot.set_xticklabels([f'{int(t)}' for t in np.arange(1, 15, step=1)],
                       weight='bold')

# diagonal break markers between the two panels
_d = 0.015
for _axb, _y1, _y2 in ((ax_top, -_d, _d), (ax_bot, 1 - _d, 1 + _d)):
    _kwargs = dict(transform=_axb.transAxes, color='black', clip_on=False,
                   linewidth=1.5)
    _axb.plot((-_d, +_d), (_y1, _y2), **_kwargs)

figure.text(0.03, 0.52, 'Lifecycle CUE ($kgCO_{2}\,eq\,/\,kWh$)',
            va='center', rotation='vertical', family='Arial',
            weight='bold', fontsize=14)
ax_bot.set_xlabel('Lifespan of satellite or server (years)',
                  family='Arial', weight='bold')

# figure.savefig(str(script_dir / 'Path3_power_density_break_even.pdf'),
#                format='pdf', dpi=1000, bbox_inches='tight')
figure.savefig(str(script_dir / 'Path3_power_density_break_even.svg'),
               format='svg', dpi=1000, bbox_inches='tight')
plt.show()
