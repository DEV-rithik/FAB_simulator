"""
Semiconductor Fab Yield Simulator — Step 1
SKY130 Process · Monte Carlo · Wafer Map · Pareto Analysis

Run: python step1_yield_simulation.py
Outputs: yield_simulation.png, pareto_yield_loss.png
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
from scipy import stats
import os

np.random.seed(42)
print("=" * 55)
print("  Semiconductor Fab Yield Simulator")
print("  SKY130 130nm Process · Monte Carlo Analysis")
print("=" * 55)

# ── 1. PROCESS PARAMETERS ─────────────────────────────────
# Values sourced from SKY130 PDK SPICE models
# github.com/google/skywater-pdk

PROCESS_PARAMS = {
    "vth0": {
        "nominal": 0.42,
        "sigma": 0.038,
        "unit": "V",
        "name": "Threshold voltage (Vth0)",
    },
    "tox": {
        "nominal": 4.1,
        "sigma": 0.22,
        "unit": "nm",
        "name": "Gate oxide thickness (Tox)",
    },
    "u0": {
        "nominal": 400.0,
        "sigma": 24.0,
        "unit": "cm²/Vs",
        "name": "Carrier mobility (u0)",
    },
}

# Pass/fail spec limits at final electrical test
SPEC_LIMITS = {
    "vth0": (0.35, 0.50),   # V
    "tox":  (3.70, 4.50),   # nm
    "u0":   (355.0, 445.0), # cm²/Vs
}

print("\n[1/5] Process parameters loaded")
print(f"      {'Parameter':<30} {'Nominal':>10}  {'Sigma':>8}  Spec window")
print(f"      {'-'*68}")
for p, v in PROCESS_PARAMS.items():
    lo, hi = SPEC_LIMITS[p]
    print(f"      {v['name']:<30} {v['nominal']:>10.3g} {v['unit']}  "
          f"±{v['sigma']:.3g}  [{lo}, {hi}]")


# ── 2. WAFER GEOMETRY ─────────────────────────────────────
def build_wafer(wafer_diameter_mm=300, die_size_mm=5.0):
    """Place dies on a circular 300mm wafer. Returns a DataFrame."""
    radius = wafer_diameter_mm / 2
    dies = []
    n = int(wafer_diameter_mm / die_size_mm) + 2

    for row in range(n):
        for col in range(n):
            x = (col * die_size_mm) - radius + die_size_mm / 2
            y = (row * die_size_mm) - radius + die_size_mm / 2

            # All four corners must sit inside the wafer circle
            corners = [
                (x - die_size_mm / 2, y - die_size_mm / 2),
                (x + die_size_mm / 2, y - die_size_mm / 2),
                (x - die_size_mm / 2, y + die_size_mm / 2),
                (x + die_size_mm / 2, y + die_size_mm / 2),
            ]
            if all(cx ** 2 + cy ** 2 <= radius ** 2 for cx, cy in corners):
                edge_dist = radius - np.sqrt(x ** 2 + y ** 2)
                dies.append(
                    {"row": row, "col": col, "x": x, "y": y,
                     "edge_distance": edge_dist}
                )

    return pd.DataFrame(dies)


wafer = build_wafer()
print(f"\n[2/5] Wafer geometry built")
print(f"      Wafer diameter : 300 mm")
print(f"      Die size       : 5 mm × 5 mm")
print(f"      Total dies     : {len(wafer)}")


# ── 3. MONTE CARLO SIMULATION ─────────────────────────────
def simulate_die(edge_distance_mm):
    """
    Sample all process parameters for one die.
    Edge dies get extra variation (±40%) to model
    real etch-rate and temperature non-uniformity.
    Returns (passed: bool, sampled_values: dict)
    """
    edge_factor = 1.0 + 0.4 * np.exp(-edge_distance_mm / 20.0)

    sampled = {}
    for param, p in PROCESS_PARAMS.items():
        sampled[param] = np.random.normal(
            p["nominal"], p["sigma"] * edge_factor
        )

    passed = all(
        lo <= sampled[param] <= hi
        for param, (lo, hi) in SPEC_LIMITS.items()
    )
    return passed, sampled


def run_wafer(wafer_df, samples_per_die=20):
    """Simulate every die on one wafer. Returns results DataFrame."""
    rows = []
    for _, die in wafer_df.iterrows():
        passes = 0
        vth_vals, tox_vals, u0_vals = [], [], []

        for _ in range(samples_per_die):
            passed, s = simulate_die(die["edge_distance"])
            if passed:
                passes += 1
            vth_vals.append(s["vth0"])
            tox_vals.append(s["tox"])
            u0_vals.append(s["u0"])

        rows.append({
            "x":    die["x"],
            "y":    die["y"],
            "pass": passes / samples_per_die,
            "vth0": np.mean(vth_vals),
            "tox":  np.mean(tox_vals),
            "u0":   np.mean(u0_vals),
        })
    return pd.DataFrame(rows)


print("\n[3/5] Running Monte Carlo simulation")
print("      Simulating 10,000 virtual wafers — please wait...")

# 10,000 wafer lot simulation (fast single-sample per die)
all_yields = []
for i in range(10000):
    results = []
    for _, die in wafer.iterrows():
        passed, _ = simulate_die(die["edge_distance"])
        results.append(passed)
    all_yields.append(np.mean(results) * 100)
    if (i + 1) % 2000 == 0:
        print(f"      ... {i+1}/10,000 wafers done")

# One detailed run for the wafer map (20 samples per die)
detailed = run_wafer(wafer, samples_per_die=20)

mean_yield = np.mean(all_yields)
std_yield  = np.std(all_yields)
worst      = np.min(all_yields)
best       = np.max(all_yields)

print(f"\n      ✓ Simulation complete")
print(f"      Mean yield  : {mean_yield:.1f}%")
print(f"      Std dev     : {std_yield:.1f}%")
print(f"      Best wafer  : {best:.1f}%")
print(f"      Worst wafer : {worst:.1f}%")


# ── 4. WAFER MAP + HISTOGRAM ──────────────────────────────
def plot_wafer_map():
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#0f1117")
    fig.suptitle(
        "SKY130 130nm Process — Yield Simulation (10,000 wafers)",
        color="white", fontsize=14, y=1.01
    )

    # ── Left: wafer die map ──────────────────────────────
    ax = axes[0]
    ax.set_facecolor("#1a1d27")
    ax.set_aspect("equal")

    # Wafer background circle
    ax.add_patch(plt.Circle((0, 0), 150, color="#1e2235", zorder=0))
    ax.add_patch(plt.Circle((0, 0), 150, color="#3a4060",
                             fill=False, linewidth=1.5, zorder=5))

    cmap = LinearSegmentedColormap.from_list(
        "yield", ["#ef4444", "#f97316", "#eab308", "#22c55e"]
    )
    die_size = 5.0

    for _, die in detailed.iterrows():
        color = cmap(die["pass"])
        ax.add_patch(patches.Rectangle(
            (die["x"] - die_size / 2, die["y"] - die_size / 2),
            die_size, die_size,
            linewidth=0.2, edgecolor="#0f1117",
            facecolor=color, zorder=2
        ))

    # Colorbar
    sm = plt.cm.ScalarMappable(
        cmap=cmap, norm=plt.Normalize(0, 1)
    )
    cbar = plt.colorbar(sm, ax=ax, shrink=0.72, pad=0.03)
    cbar.set_label("Pass probability", color="#9ca3af", fontsize=9)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#9ca3af", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="#4b5563")

    # Flat zone
    ax.plot([-150, -135], [0, 0], color="#4a4f6a", linewidth=3, zorder=6)

    # Annotations
    ax.text(0, -170, f"Mean yield: {mean_yield:.1f}% ± {std_yield:.1f}%",
            color="white", fontsize=11, ha="center", fontweight="bold")
    ax.text(0, -183, f"{len(wafer)} dies  |  5mm × 5mm  |  300mm wafer",
            color="#6b7280", fontsize=8, ha="center")

    ax.set_xlim(-175, 175)
    ax.set_ylim(-195, 175)
    ax.set_title("Wafer yield map", color="white", fontsize=12, pad=10)
    ax.set_xlabel("X (mm)", color="#9ca3af", fontsize=9)
    ax.set_ylabel("Y (mm)", color="#9ca3af", fontsize=9)
    ax.tick_params(colors="#6b7280", labelsize=8)
    for s in ax.spines.values():
        s.set_edgecolor("#2d3142")

    # ── Right: yield distribution histogram ──────────────
    ax2 = axes[1]
    ax2.set_facecolor("#1a1d27")

    n, bins, patches_hist = ax2.hist(
        all_yields, bins=60,
        color="#22c55e", alpha=0.75,
        edgecolor="#16a34a", linewidth=0.4
    )

    # Shade ±1σ region
    lo1, hi1 = mean_yield - std_yield, mean_yield + std_yield
    ax2.axvspan(lo1, hi1, alpha=0.12, color="#22c55e", label=f"±1σ window")

    ax2.axvline(mean_yield, color="white", linewidth=1.8,
                linestyle="--", label=f"Mean: {mean_yield:.1f}%")
    ax2.axvline(mean_yield - 2 * std_yield, color="#ef4444",
                linewidth=1.2, linestyle=":",
                label=f"−2σ: {mean_yield - 2*std_yield:.1f}%")

    # Normal fit overlay
    x_fit = np.linspace(min(all_yields), max(all_yields), 300)
    y_fit = stats.norm.pdf(x_fit, mean_yield, std_yield)
    scale = (bins[1] - bins[0]) * len(all_yields)
    ax2.plot(x_fit, y_fit * scale, color="#60a5fa",
             linewidth=1.5, linestyle="-", alpha=0.8, label="Normal fit")

    ax2.set_title("Yield distribution (10,000 wafers)",
                  color="white", fontsize=12, pad=10)
    ax2.set_xlabel("Yield (%)", color="#9ca3af", fontsize=9)
    ax2.set_ylabel("Wafer count", color="#9ca3af", fontsize=9)
    ax2.tick_params(colors="#6b7280", labelsize=8)
    ax2.legend(facecolor="#1e2130", edgecolor="#2d3142",
               labelcolor="white", fontsize=9)
    for s in ax2.spines.values():
        s.set_edgecolor("#2d3142")

    # Stats box
    stats_text = (
        f"μ  =  {mean_yield:.2f}%\n"
        f"σ  =  {std_yield:.2f}%\n"
        f"Min = {worst:.1f}%\n"
        f"Max = {best:.1f}%"
    )
    ax2.text(0.97, 0.97, stats_text,
             transform=ax2.transAxes,
             color="white", fontsize=9,
             va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.5",
                       facecolor="#1e2130",
                       edgecolor="#2d3142", alpha=0.9),
             fontfamily="monospace")

    plt.tight_layout(pad=2.5)
    out = "yield_simulation.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                facecolor="#0f1117")
    plt.show()
    print(f"\n[4/5] Wafer map saved → {out}")


plot_wafer_map()


# ── 5. PARETO CHART OF YIELD LOSS ─────────────────────────
def plot_pareto():
    print("\n[5/5] Computing yield loss per parameter...")

    contributors = {}
    N = 5000

    for param, (lo, hi) in SPEC_LIMITS.items():
        p = PROCESS_PARAMS[param]
        samples = np.random.normal(p["nominal"], p["sigma"], N)
        fail_rate = np.mean((samples < lo) | (samples > hi)) * 100
        contributors[p["name"]] = round(fail_rate, 2)

    sorted_c  = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
    names     = [x[0] for x in sorted_c]
    losses    = [x[1] for x in sorted_c]
    bar_colors = ["#ef4444", "#f97316", "#eab308"]

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d27")

    bars = ax.barh(
        names, losses,
        color=bar_colors[: len(names)],
        edgecolor="#0f1117", linewidth=0.5,
        height=0.45
    )

    for bar, loss in zip(bars, losses):
        ax.text(
            bar.get_width() + 0.05,
            bar.get_y() + bar.get_height() / 2,
            f"  {loss:.1f}% yield loss",
            va="center", color="white", fontsize=10
        )

    ax.set_title(
        "Yield loss by process parameter — Pareto analysis\n"
        "Fix the top bar first for maximum yield improvement",
        color="white", fontsize=12, pad=12
    )
    ax.set_xlabel("Yield loss contribution (%)", color="#9ca3af", fontsize=9)
    ax.set_xlim(0, max(losses) * 1.35)
    ax.tick_params(colors="#9ca3af", labelsize=9)
    for s in ax.spines.values():
        s.set_edgecolor("#2d3142")

    plt.tight_layout(pad=2.0)
    out = "pareto_yield_loss.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                facecolor="#0f1117")
    plt.show()
    print(f"      Pareto chart saved → {out}")
    print(f"\n      Top yield loss driver : {names[0]} ({losses[0]:.1f}%)")
    print(f"      → Tighten this parameter first for best ROI")


plot_pareto()

print("\n" + "=" * 55)
print("  Done. Two output images saved in this folder:")
print("  → yield_simulation.png")
print("  → pareto_yield_loss.png")
print("=" * 55)
