# micrograd/filter_sensitivity.py
"""
Filter radius sensitivity study:
Runs the topology optimisation on the same mesh with different r_filter values,
and compares final topologies, objective values, and outlet profiles.
Generates a multi‑panel figure for the paper.
"""
import numpy as np
import matplotlib.pyplot as plt
import os
import dolfinx
from dolfinx import fem
import ufl

from .gradient_optimizer import GradientGeneratorOptimizer


def compute_rmse_outlet(c_h, target_expr, boundary_data):
    """Compute RMSE of concentration at outlet."""
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]
    fdim = c_h.function_space.mesh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x = V_conc.tabulate_dof_coordinates()[dofs]
    y = x[:, 1]
    c_vals = c_h.vector.array[dofs]
    idx = np.argsort(y)
    y = y[idx]; c_vals = c_vals[idx]
    target_vals = target_expr(np.array([np.zeros_like(y), y]))
    rmse = np.sqrt(np.mean((c_vals - target_vals)**2))
    return rmse


def run_filter_sensitivity(target_expr, Lx=2000e-6, Ly=500e-6,
                           nx=80, ny=20,
                           r_filter_multipliers=[1.0, 1.5, 2.0, 2.5, 3.0],
                           output_dir="filter_sensitivity",
                           max_iter=80):
    """
    Run optimisation with different filter radii.
    Element size: h = Lx / nx.
    r_filter = multiplier * h.
    """
    os.makedirs(output_dir, exist_ok=True)
    h = Lx / nx
    results = []

    for mult in r_filter_multipliers:
        r_f = mult * h
        print(f"\n=== Filter radius = {r_f*1e6:.1f} µm (multiplier = {mult}) ===")
        opt = GradientGeneratorOptimizer(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                                         target_expr=target_expr,
                                         V_star=0.5,
                                         w_f=1e-7, w_c=1.0)
        opt.r_filter = r_f
        rho_phys = opt.run(max_iter=max_iter,
                           beta_continuation=[1, 2, 4, 8, 16],
                           move=0.2)

        # Collect metrics
        J_total = opt.history[-1, 2]
        J_flow = opt.history[-1, 3]
        J_conc = opt.history[-1, 4]
        outlet_rmse = compute_rmse_outlet(opt.c_h, target_expr, opt.boundary_data)

        results.append({
            'multiplier': mult,
            'r_filter': r_f,
            'J_total': J_total,
            'J_flow': J_flow,
            'J_conc': J_conc,
            'outlet_rmse': outlet_rmse,
            'rho_phys': rho_phys,
            'c_h': opt.c_h,
            'boundary_data': opt.boundary_data,
            'msh': opt.msh,
            'V_rho': opt.V_rho,
            'history': opt.history,
            'optimizer': opt
        })

    # --- Generate figures ---
    # 1. Convergence histories
    plt.figure(figsize=(10,5))
    for r in results:
        hist = r['history']
        plt.plot(hist[:,0], hist[:,2], label=f"$r_f = {r['r_filter']*1e6:.1f}$ µm")
    plt.xlabel('Iteration')
    plt.ylabel('Total objective J')
    plt.legend()
    plt.title('Convergence for different filter radii')
    plt.savefig(os.path.join(output_dir, "filter_convergence.png"), dpi=150)
    plt.close()

    # 2. Outlet profiles
    plt.figure(figsize=(8,5))
    y_plot = np.linspace(0, Ly, 100)
    target_vals = target_expr(np.array([np.zeros_like(y_plot), y_plot]))
    plt.plot(y_plot*1e6, target_vals, 'k--', linewidth=2, label='Target')
    for r in results:
        c_h = r['c_h']
        bnd = r['boundary_data']
        V_conc = c_h.function_space
        outlet_facets = bnd["outlet"]
        fdim = r['msh'].topology.dim - 1
        dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
        x = V_conc.tabulate_dof_coordinates()[dofs]
        y = x[:, 1]
        c_vals = c_h.vector.array[dofs]
        idx = np.argsort(y)
        plt.plot(y[idx]*1e6, c_vals[idx], '-', label=f"$r_f = {r['r_filter']*1e6:.1f}$ µm")
    plt.xlabel('y (µm)')
    plt.ylabel('Concentration')
    plt.legend()
    plt.title('Outlet profiles for varying filter radii')
    plt.savefig(os.path.join(output_dir, "filter_outlet_profiles.png"), dpi=150)
    plt.close()

    # 3. Topology montage (side‑by‑side density images)
    try:
        import pyvista as pv
        n = len(results)
        fig, axes = plt.subplots(1, n, figsize=(4*n, 4))
        if n == 1: axes = [axes]
        for ax, r in zip(axes, results):
            topology, cells, geometry = dolfinx.plot.vtk_mesh(r['V_rho'])
            grid = pv.UnstructuredGrid(cells, geometry, topology)
            grid["density"] = r['rho_phys'].vector.array.real
            plotter = pv.Plotter(off_screen=True)
            plotter.add_mesh(grid, cmap="coolwarm", show_edges=False, clim=[0,1])
            plotter.view_xy()
            img = plotter.screenshot(return_img=True)
            ax.imshow(img)
            ax.set_title(f"$r_f = {r['r_filter']*1e6:.1f}$ µm")
            ax.axis('off')
            plotter.close()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "filter_topologies.png"), dpi=200)
        plt.close()
    except Exception as e:
        print("Could not render topology comparison:", e)

    # 4. Bar chart of outlet RMSE vs. filter radius
    plt.figure(figsize=(6,4))
    multipliers = [r['multiplier'] for r in results]
    rmses = [r['outlet_rmse'] for r in results]
    plt.bar(multipliers, rmses, width=0.1)
    plt.xlabel('Filter radius multiplier (× element size)')
    plt.ylabel('Outlet RMSE')
    plt.title('Sensitivity of outlet error to filter radius')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "filter_rmse_bar.png"), dpi=150)
    plt.close()

    # Save metrics to CSV
    csv_path = os.path.join(output_dir, "filter_metrics.csv")
    with open(csv_path, 'w') as f:
        f.write("multiplier,r_filter_um,J_total,J_flow,J_conc,outlet_rmse\n")
        for r in results:
            f.write(f"{r['multiplier']},{r['r_filter']*1e6:.2f},{r['J_total']:.6e},{r['J_flow']:.6e},{r['J_conc']:.6e},{r['outlet_rmse']:.6e}\n")

    print(f"\nFilter sensitivity study completed. Results in {output_dir}")
    return results