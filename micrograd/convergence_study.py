# micrograd/convergence_study.py
"""
Mesh convergence study for the topology optimisation of microfluidic gradient generators.
Runs the optimisation on coarse, medium, and fine meshes; compares objective values,
viscous dissipation, outlet profile error, and final topologies.
"""
import numpy as np
import matplotlib.pyplot as plt
import os
from .gradient_optimizer import GradientGeneratorOptimizer
from dolfinx import fem
from .validation import compute_rmse_outlet


def run_convergence_study(target_expr, Lx=2000e-6, Ly=500e-6,
                          mesh_sizes=[(40, 10), (80, 20), (160, 40)],
                          output_dir="convergence_study",
                          max_iter=80, V_star=0.5):
    """
    Run optimisation on multiple meshes, collect metrics, and generate plots.

    Args:
        target_expr: callable target concentration profile.
        Lx, Ly: domain dimensions (m).
        mesh_sizes: list of (nx, ny) tuples.
        output_dir: directory for saving figures and CSV.
        max_iter: number of optimisation iterations per mesh.
        V_star: target fluid volume fraction.

    Returns:
        list of dicts with metrics for each mesh.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for nx, ny in mesh_sizes:
        print(f"\n=== Mesh {nx}×{ny} ===")
        opt = GradientGeneratorOptimizer(Lx=Lx, Ly=Ly, nx=nx, ny=ny,
                                         target_expr=target_expr,
                                         V_star=V_star,
                                         w_f=1e-7, w_c=1.0)
        # Set filter radius to 2× element size (approx)
        dx = Lx / nx
        opt.r_filter = 2 * dx
        rho_phys = opt.run(max_iter=max_iter,
                           beta_continuation=[1, 2, 4, 8, 16],
                           move=0.2)

        # Metrics from last iteration
        J_total = opt.history[-1, 2]   # col 2 = total objective
        J_flow  = float('nan')          # not tracked separately
        J_conc  = float('nan')          # not tracked separately
        outlet_rmse = compute_rmse_outlet(opt.c_h, target_expr, opt.boundary_data)

        results.append({
            'mesh_label': f'{nx}×{ny}',
            'nx': nx, 'ny': ny,
            'history': opt.history,
            'rho_phys': rho_phys,
            'J_total': J_total,
            'J_flow': J_flow,
            'J_conc': J_conc,
            'outlet_rmse': outlet_rmse,
            'c_h': opt.c_h,
            'boundary_data': opt.boundary_data,
            'msh': opt.msh,
            'V_rho': opt.V_rho,
            'optimizer': opt   # keep for density plotting if needed
        })

    # --- Generate comparison table and figures ---
    # Table: save to CSV
    csv_path = os.path.join(output_dir, "convergence_metrics.csv")
    with open(csv_path, 'w') as f:
        f.write("mesh,J_total,J_flow,J_conc,outlet_rmse\n")
        for r in results:
            f.write(f"{r['mesh_label']},{r['J_total']:.6e},{r['J_flow']:.6e},{r['J_conc']:.6e},{r['outlet_rmse']:.6e}\n")
    print(f"Metrics saved to {csv_path}")

    # Figure 1: Convergence of total objective for each mesh
    plt.figure(figsize=(10,5))
    for r in results:
        hist = r['history']
        plt.plot(hist[:,0], hist[:,2], label=r['mesh_label'])
    plt.xlabel('Iteration')
    plt.ylabel('Total objective J')
    plt.legend()
    plt.title('Convergence history (mesh study)')
    plt.savefig(os.path.join(output_dir, "convergence_history.png"), dpi=150)
    plt.close()

    # Figure 2: Final topologies side by side
        import dolfinx
        n_meshes = len(results)
        fig, axes = plt.subplots(1, n_meshes, figsize=(4*n_meshes, 4))
        if n_meshes == 1:
            axes = [axes]
        for ax, r in zip(axes, results):
            topology, cells, geometry = dolfinx.plot.vtk_mesh(r['V_rho'])
            grid["density"] = r['rho_phys'].x.array.real
            plotter.add_mesh(grid, cmap="coolwarm", show_edges=False, clim=[0,1])
            plotter.view_xy()
            img = plotter.screenshot(return_img=True)
            ax.imshow(img)
            ax.set_title(r['mesh_label'])
            ax.axis('off')
            plotter.close()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "topology_comparison.png"), dpi=200)
        plt.close()
    except Exception as e:
        print("Could not generate topology comparison figure:", e)

    # Figure 3: Outlet concentration profiles for all meshes
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
        c_vals = c_h.x.array[dofs]
        idx = np.argsort(y)
        plt.plot(y[idx]*1e6, c_vals[idx], '-o', markersize=2, label=r['mesh_label'])
    plt.xlabel('y (µm)')
    plt.ylabel('Concentration')
    plt.legend()
    plt.title('Outlet profiles (mesh study)')
    plt.savefig(os.path.join(output_dir, "outlet_profiles.png"), dpi=150)
    plt.close()

    return results

if __name__ == "__main__":
    run_convergence_study(lambda x: x[1]/500e-6,
        mesh_sizes=[(40,10),(80,20),(160,40)],
        output_dir="figures", max_iter=60)