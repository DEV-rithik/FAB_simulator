"""
Simulator service — wraps the FAB yield simulation logic and
persists results to a SimulationRun model instance.

Keeps all simulation behaviour identical to step1_yield_simulation.py;
only the I/O (file paths, random seed) is adapted for web use.
"""

import io
import os
import uuid

import matplotlib
matplotlib.use('Agg')  # non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from scipy import stats
from django.core.files.base import ContentFile


# ── Default process parameters (from SKY130 PDK) ───────────────────────────
DEFAULT_PROCESS_PARAMS = {
    "vth0": {"nominal": 0.42, "sigma": 0.038, "unit": "V",         "name": "Threshold voltage (Vth0)"},
    "tox":  {"nominal": 4.1,  "sigma": 0.22,  "unit": "nm",        "name": "Gate oxide thickness (Tox)"},
    "u0":   {"nominal": 400.0,"sigma": 24.0,  "unit": "cm²/Vs",   "name": "Carrier mobility (u0)"},
}

DEFAULT_SPEC_LIMITS = {
    "vth0": (0.35, 0.50),
    "tox":  (3.70, 4.50),
    "u0":   (355.0, 445.0),
}


# ── Wafer geometry ──────────────────────────────────────────────────────────
def _build_wafer(wafer_diameter_mm=300, die_size_mm=5.0):
    radius = wafer_diameter_mm / 2
    dies = []
    n = int(wafer_diameter_mm / die_size_mm) + 2
    for row in range(n):
        for col in range(n):
            x = col * die_size_mm - radius + die_size_mm / 2
            y = row * die_size_mm - radius + die_size_mm / 2
            corners = [
                (x - die_size_mm / 2, y - die_size_mm / 2),
                (x + die_size_mm / 2, y - die_size_mm / 2),
                (x - die_size_mm / 2, y + die_size_mm / 2),
                (x + die_size_mm / 2, y + die_size_mm / 2),
            ]
            if all(cx ** 2 + cy ** 2 <= radius ** 2 for cx, cy in corners):
                edge_dist = radius - np.sqrt(x ** 2 + y ** 2)
                dies.append({"row": row, "col": col, "x": x, "y": y, "edge_distance": edge_dist})
    return pd.DataFrame(dies)


# ── Monte Carlo die simulation ──────────────────────────────────────────────
def _simulate_die(edge_distance_mm, process_params, spec_limits):
    edge_factor = 1.0 + 0.4 * np.exp(-edge_distance_mm / 20.0)
    sampled = {}
    for param, p in process_params.items():
        sampled[param] = np.random.normal(p["nominal"], p["sigma"] * edge_factor)
    passed = all(lo <= sampled[param] <= hi for param, (lo, hi) in spec_limits.items())
    return passed, sampled


def _run_wafer_detailed(wafer_df, process_params, spec_limits, samples_per_die=20):
    rows = []
    for _, die in wafer_df.iterrows():
        passes = 0
        vth_vals, tox_vals, u0_vals = [], [], []
        for _ in range(samples_per_die):
            passed, s = _simulate_die(die["edge_distance"], process_params, spec_limits)
            if passed:
                passes += 1
            vth_vals.append(s["vth0"])
            tox_vals.append(s["tox"])
            u0_vals.append(s["u0"])
        rows.append({
            "x": die["x"], "y": die["y"],
            "pass": passes / samples_per_die,
            "vth0": np.mean(vth_vals),
            "tox": np.mean(tox_vals),
            "u0": np.mean(u0_vals),
        })
    return pd.DataFrame(rows)


# ── Plot: wafer map + histogram ─────────────────────────────────────────────
def _make_wafer_map_figure(detailed, wafer, all_yields, mean_yield, std_yield, worst, best):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#0f1117")
    fig.suptitle(
        "SKY130 130nm Process — Yield Simulation",
        color="white", fontsize=14, y=1.01,
    )

    ax = axes[0]
    ax.set_facecolor("#1a1d27")
    ax.set_aspect("equal")
    ax.add_patch(plt.Circle((0, 0), 150, color="#1e2235", zorder=0))
    ax.add_patch(plt.Circle((0, 0), 150, color="#3a4060", fill=False, linewidth=1.5, zorder=5))

    cmap = LinearSegmentedColormap.from_list("yield", ["#ef4444", "#f97316", "#eab308", "#22c55e"])
    die_size = 5.0
    for _, die in detailed.iterrows():
        color = cmap(die["pass"])
        ax.add_patch(patches.Rectangle(
            (die["x"] - die_size / 2, die["y"] - die_size / 2),
            die_size, die_size,
            linewidth=0.2, edgecolor="#0f1117", facecolor=color, zorder=2,
        ))

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    cbar = plt.colorbar(sm, ax=ax, shrink=0.72, pad=0.03)
    cbar.set_label("Pass probability", color="#9ca3af", fontsize=9)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#9ca3af", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="#4b5563")

    ax.plot([-150, -135], [0, 0], color="#4a4f6a", linewidth=3, zorder=6)
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

    ax2 = axes[1]
    ax2.set_facecolor("#1a1d27")
    n, bins, _ = ax2.hist(all_yields, bins=60, color="#22c55e", alpha=0.75, edgecolor="#16a34a", linewidth=0.4)
    lo1, hi1 = mean_yield - std_yield, mean_yield + std_yield
    ax2.axvspan(lo1, hi1, alpha=0.12, color="#22c55e", label=f"±1σ window")
    ax2.axvline(mean_yield, color="white", linewidth=1.8, linestyle="--", label=f"Mean: {mean_yield:.1f}%")
    ax2.axvline(mean_yield - 2 * std_yield, color="#ef4444", linewidth=1.2, linestyle=":",
                label=f"−2σ: {mean_yield - 2*std_yield:.1f}%")

    x_fit = np.linspace(min(all_yields), max(all_yields), 300)
    y_fit = stats.norm.pdf(x_fit, mean_yield, std_yield)
    scale = (bins[1] - bins[0]) * len(all_yields)
    ax2.plot(x_fit, y_fit * scale, color="#60a5fa", linewidth=1.5, linestyle="-", alpha=0.8, label="Normal fit")

    ax2.set_title("Yield distribution", color="white", fontsize=12, pad=10)
    ax2.set_xlabel("Yield (%)", color="#9ca3af", fontsize=9)
    ax2.set_ylabel("Wafer count", color="#9ca3af", fontsize=9)
    ax2.tick_params(colors="#6b7280", labelsize=8)
    ax2.legend(facecolor="#1e2130", edgecolor="#2d3142", labelcolor="white", fontsize=9)
    for s in ax2.spines.values():
        s.set_edgecolor("#2d3142")

    stats_text = (f"μ  =  {mean_yield:.2f}%\nσ  =  {std_yield:.2f}%\n"
                  f"Min = {worst:.1f}%\nMax = {best:.1f}%")
    ax2.text(0.97, 0.97, stats_text, transform=ax2.transAxes, color="white", fontsize=9,
             va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#1e2130", edgecolor="#2d3142", alpha=0.9),
             fontfamily="monospace")

    plt.tight_layout(pad=2.5)
    return fig


# ── Plot: Pareto chart ──────────────────────────────────────────────────────
def _make_pareto_figure(contributors_sorted):
    names = [x[0] for x in contributors_sorted]
    losses = [x[1] for x in contributors_sorted]
    bar_colors = ["#ef4444", "#f97316", "#eab308"]

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d27")

    bars = ax.barh(names, losses, color=bar_colors[: len(names)],
                   edgecolor="#0f1117", linewidth=0.5, height=0.45)
    for bar, loss in zip(bars, losses):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                f"  {loss:.1f}% yield loss", va="center", color="white", fontsize=10)

    ax.set_title(
        "Yield loss by process parameter — Pareto analysis\n"
        "Fix the top bar first for maximum yield improvement",
        color="white", fontsize=12, pad=12,
    )
    ax.set_xlabel("Yield loss contribution (%)", color="#9ca3af", fontsize=9)
    ax.set_xlim(0, max(losses) * 1.35 if losses else 1)
    ax.tick_params(colors="#9ca3af", labelsize=9)
    for s in ax.spines.values():
        s.set_edgecolor("#2d3142")

    plt.tight_layout(pad=2.0)
    return fig


# ── Main entry point ────────────────────────────────────────────────────────
def run_simulation(simulation_run):
    """
    Execute the FAB yield simulation and persist results to *simulation_run*.

    Parameters
    ----------
    simulation_run : SimulationRun
        A model instance with ``input_payload`` already populated.
        The instance is saved with results (or error) before returning.
    """
    try:
        inp = simulation_run.input_payload

        # Parse inputs with defaults
        wafer_diameter = float(inp.get("wafer_diameter_mm", 300))
        die_size = float(inp.get("die_size_mm", 5.0))
        mc_runs = int(inp.get("mc_runs", 10000))
        mc_runs = max(100, min(mc_runs, 50000))  # clamp to safe range

        # Allow per-run process parameter overrides
        process_params = dict(DEFAULT_PROCESS_PARAMS)
        for key in ("vth0", "tox", "u0"):
            if f"{key}_nominal" in inp or f"{key}_sigma" in inp:
                process_params[key] = dict(DEFAULT_PROCESS_PARAMS[key])
                if f"{key}_nominal" in inp:
                    process_params[key]["nominal"] = float(inp[f"{key}_nominal"])
                if f"{key}_sigma" in inp:
                    process_params[key]["sigma"] = float(inp[f"{key}_sigma"])

        spec_limits = dict(DEFAULT_SPEC_LIMITS)

        # Reproducible seed derived from run PK so each run is deterministic
        np.random.seed(simulation_run.pk % (2**31))

        # Build wafer
        wafer = _build_wafer(wafer_diameter_mm=wafer_diameter, die_size_mm=die_size)

        # Monte Carlo lot simulation
        all_yields = []
        for _ in range(mc_runs):
            results = [_simulate_die(die["edge_distance"], process_params, spec_limits)[0]
                       for _, die in wafer.iterrows()]
            all_yields.append(np.mean(results) * 100)

        # Detailed single run for wafer map
        detailed = _run_wafer_detailed(wafer, process_params, spec_limits, samples_per_die=20)

        mean_yield = float(np.mean(all_yields))
        std_yield = float(np.std(all_yields))
        worst = float(np.min(all_yields))
        best = float(np.max(all_yields))

        # Pareto analysis
        contributors = {}
        N = 5000
        for param, (lo, hi) in spec_limits.items():
            p = process_params[param]
            samples = np.random.normal(p["nominal"], p["sigma"], N)
            fail_rate = float(np.mean((samples < lo) | (samples > hi)) * 100)
            contributors[p["name"]] = round(fail_rate, 2)
        contributors_sorted = sorted(contributors.items(), key=lambda x: x[1], reverse=True)

        # ── Save wafer map figure ──────────────────────────────────────────
        fig1 = _make_wafer_map_figure(detailed, wafer, all_yields, mean_yield, std_yield, worst, best)
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format="png", dpi=120, bbox_inches="tight", facecolor="#0f1117")
        plt.close(fig1)
        buf1.seek(0)
        fname1 = f"wafer_map_{uuid.uuid4().hex[:8]}.png"
        simulation_run.wafer_map_image.save(fname1, ContentFile(buf1.read()), save=False)

        # ── Save pareto figure ─────────────────────────────────────────────
        fig2 = _make_pareto_figure(contributors_sorted)
        buf2 = io.BytesIO()
        fig2.savefig(buf2, format="png", dpi=120, bbox_inches="tight", facecolor="#0f1117")
        plt.close(fig2)
        buf2.seek(0)
        fname2 = f"pareto_{uuid.uuid4().hex[:8]}.png"
        simulation_run.pareto_image.save(fname2, ContentFile(buf2.read()), save=False)

        # ── Persist summary ────────────────────────────────────────────────
        simulation_run.mean_yield = mean_yield
        simulation_run.std_yield = std_yield
        simulation_run.best_yield = best
        simulation_run.worst_yield = worst
        simulation_run.total_dies = len(wafer)
        simulation_run.result_payload = {
            "pareto": contributors_sorted,
            "process_params": {k: {"nominal": v["nominal"], "sigma": v["sigma"], "unit": v["unit"]}
                               for k, v in process_params.items()},
            "spec_limits": {k: list(v) for k, v in spec_limits.items()},
            # Store a sample of yields for potential CSV export
            "yield_sample": [round(y, 4) for y in all_yields[:500]],
        }
        simulation_run.status = "completed"
        simulation_run.save()

    except Exception as exc:  # noqa: BLE001
        simulation_run.status = "failed"
        simulation_run.error_message = str(exc)
        simulation_run.save()
        raise
