# micrograd/multiobjective.py
"""
Multi‑objective Pareto analysis via weight‑ratio sweep.
Sweeps the flow dissipation weight w_f while keeping the concentration mismatch
weight w_c = 1.0 to reveal the trade‑off between hydraulic efficiency and
concentration fidelity.
"""
import numpy as np
import matplotlib.pyplot as plt
import os
from .gradient_optimizer import GradientGeneratorOptimizer
from .experimental_metrics import compute_metrics


def run_pareto_sweep(target_expr, Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                     w_f_values=None, max_iter=80, V_star=0.5,
                     output_dir="pareto"):
    """
    Run topology optimisation for a range of w_f values (with w_c = 1.0).
    
    For each w_f, the optimiser is run and the following metrics are collected:
      - Outlet RMSE
      - Viscous dissipation J_f (from the last iteration)
      - Hydraulic resistance (Pa·s/m³)
    
    A Pareto front plot (dissipation vs. RMSE) and a second plot (hydraulic
    resistance vs. RMSE) are saved, along with a summary CSV file.
    
    Args:
        target_expr: callable target concentration profile.
        Lx, Ly: domain dimensions (m).
        nx, ny: mesh resolution.
        w_f_values: list of w_f values to sweep. If None, a default log‑spaced
                    range from 1e-10 to 1e-5 (8 points) is used.
        max_iter: number of optimisation iterations per point.
        V_star: target fluid volume fraction.
        output_dir: directory in which to save figures and CSV.
        
    Returns:
        dict with keys: 'w_f', 'RMSE', 'dissipation', 'resistance' (all numpy arrays).
    """
    if w_f_values is None:
        w_f_values = np.logspace(-10, -5, 8)   # 8 points

    w_f_values = np.atleast_1d(w_f_values)
    n_points = len(w_f_values)

    os.makedirs(output_dir, exist_ok=True)

    rmses = np.zeros(n_points)
    dissipations = np.zeros(n_points)
    resistances = np.zeros(n_points)

    for i, w_f in enumerate(w_f_values):
        print(f"\n=== Pareto point {i+1}/{n_points} : w_f = {w_f:.2e} ===")
        opt = GradientGeneratorOptimizer(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                                         target_expr=target_expr,
                                         V_star=V_star,
                                         w_f=w_f, w_c=1.0)
        rho_phys = opt.run(max_iter=max_iter,
                           beta_continuation=[1, 2, 4, 8, 16],
                           V_star_schedule=None,   # use default continuation
                           method='oc')

        # Extract metrics using the experimental metrics module
        metrics = compute_metrics(opt.msh, opt.boundary_data, rho_phys,
                                  opt.u_h, opt.c_h, target_expr)

        rmses[i] = metrics['outlet_rmse']
        dissipations[i] = opt.history[-1, 3]          # J_f column in history
        resistances[i] = metrics['hydraulic_resistance_Pa_s_per_m3']

        # Save per‑point data for reproducibility
        np.savez(os.path.join(output_dir, f"point_wf_{w_f:.2e}.npz"),
                 w_f=w_f, rmse=rmses[i], dissipation=dissipations[i],
                 resistance=resistances[i])

    # ---- Pareto front: dissipation vs. RMSE ----
    plt.figure(figsize=(7, 5))
    plt.plot(dissipations, rmses, 'o-', markersize=8, linewidth=2)
    for i, wf in enumerate(w_f_values):
        plt.annotate(f'$w_f={wf:.1e}$', (dissipations[i], rmses[i]),
                     textcoords="offset points", xytext=(5, 5), fontsize=8)
    plt.xlabel('Viscous dissipation $J_f$ (W/m)')
    plt.ylabel('Outlet RMSE')
    plt.title('Pareto front: pressure drop vs. concentration error')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "pareto_dissipation_vs_rmse.pdf"))
    plt.close()

    # ---- Pareto front: hydraulic resistance vs. RMSE ----
    plt.figure(figsize=(7, 5))
    plt.plot(resistances, rmses, 's-', markersize=8, linewidth=2)
    for i, wf in enumerate(w_f_values):
        plt.annotate(f'$w_f={wf:.1e}$', (resistances[i], rmses[i]),
                     textcoords="offset points", xytext=(5, 5), fontsize=8)
    plt.xlabel('Hydraulic resistance (Pa·s/m³)')
    plt.ylabel('Outlet RMSE')
    plt.title('Pareto front: hydraulic resistance vs. concentration error')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "pareto_resistance_vs_rmse.pdf"))
    plt.close()

    # ---- Save summary CSV ----
    np.savetxt(os.path.join(output_dir, "pareto_data.csv"),
               np.column_stack((w_f_values, rmses, dissipations, resistances)),
               header="w_f,RMSE,dissipation,hydraulic_resistance",
               delimiter=",", comments="")

    print(f"Pareto sweep finished. Results saved in {output_dir}/")
    return {
        "w_f": w_f_values,
        "RMSE": rmses,
        "dissipation": dissipations,
        "resistance": resistances
    }