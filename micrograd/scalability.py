# micrograd/scalability.py
"""Scalability study: iterative solver performance on successive mesh refinements."""
import time
import numpy as np
import matplotlib.pyplot as plt
import os
from dolfinx import fem
from .mesh import create_rectangular_mesh
from .solver import forward_solve

def scalability_study(target_expr, Lx=2000e-6, Ly=500e-6,
                      resolutions=[(40,10), (80,20), (160,40), (320,80)],
                      solver_type="iterative",
                      output_dir="scalability"):
    """
    Run forward solve on each mesh with an iterative solver, record timing and
    iteration counts.

    Args:
        target_expr: unused here (kept for interface consistency).
        Lx, Ly: domain dimensions (m).
        resolutions: list of (nx, ny) tuples.
        solver_type: "direct" or "iterative".
        output_dir: directory to save the scalability plot.

    Returns:
        list of dicts with keys 'nx', 'ny', 'ndofs_flow', 'time'.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for nx, ny in resolutions:
        print(f"--- Mesh {nx}×{ny} ---")
        msh, bnd = create_rectangular_mesh(Lx, Ly, nx, ny)
        V_rho = fem.FunctionSpace(msh, ("Lagrange", 1))
        rho = fem.Function(V_rho)
        rho.vector.set(0.5)  # uniform half‑fluid for a realistic system
        rho.vector.ghostUpdate()

        t0 = time.time()
        u_h, p_h, c_h = forward_solve(msh, bnd, rho, solver_type=solver_type)
        t1 = time.time()

        # Velocity degrees of freedom (total number of vector components)
        ndofs_flow = (u_h.function_space.dofmap.index_map.size_global *
                      u_h.function_space.mesh.geometry.dim)

        results.append({
            'nx': nx, 'ny': ny,
            'ndofs_flow': ndofs_flow,
            'time': t1 - t0,
        })
        print(f"  DOFs = {ndofs_flow}, time = {t1-t0:.2f} s")

    # ---- Plot scalability ----
    ndofs = [r['ndofs_flow'] for r in results]
    times = [r['time'] for r in results]

    plt.figure(figsize=(7, 5))
    plt.loglog(ndofs, times, 'o-', markersize=8, label=solver_type)
    if len(ndofs) > 1:
        slope = np.polyfit(np.log(ndofs), np.log(times), 1)[0]
        plt.title(f"Scalability (slope ≈ {slope:.2f})")
    plt.xlabel('Number of velocity dofs')
    plt.ylabel('Solve time [s]')
    plt.legend()
    plt.grid(True, which='both')
    plt.savefig(os.path.join(output_dir, "scalability.png"), dpi=150)
    plt.close()

    return results