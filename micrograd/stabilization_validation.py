# micrograd/stabilization_validation.py
"""
Stabilisation validation for convection‑diffusion:
Compares unstabilised (pure Galerkin), SUPG, and GLS solutions on a given
velocity and density field, typically from a coarse‑mesh optimisation.
"""
import numpy as np
import ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
from petsc4py import PETSc


def solve_convection_diffusion(msh, boundary_data, rho_phys, u_h,
                               D_fluid=1e-9, D_eff_func=None, method="supg"):
    """
    Solve steady convection‑diffusion on the given mesh with prescribed velocity u_h
    and effective diffusivity D_eff_func (or constant if None).
    method : 'none', 'supg', 'gls'
    Returns concentration field c_h.
    """
    if D_eff_func is None:
        from .utilities import D_eff as D_eff_func

    V_conc = fem.FunctionSpace(msh, ("Lagrange", 1))
    c = ufl.TrialFunction(V_conc)
    v = ufl.TestFunction(V_conc)

    D = D_eff_func(rho_phys) if D_eff_func else fem.Constant(msh, D_fluid)
    u = u_h

    # Cell diameter and stabilisation parameter
    h = ufl.CellDiameter(msh)
    u_mag = ufl.sqrt(ufl.dot(u, u) + 1e-20)
    Pe = u_mag * h / (2.0 * D)
    tau = h / (2.0 * u_mag) * (1.0 / ufl.tanh(Pe) - 1.0 / Pe)

    # Galerkin part (same for all)
    a_galerkin = (ufl.dot(u, ufl.grad(c)) * v * ufl.dx
                  + D * ufl.inner(ufl.grad(c), ufl.grad(v)) * ufl.dx)
    L = fem.Constant(msh, 0.0) * v * ufl.dx

    if method == "none":
        a = a_galerkin
    elif method == "supg":
        a = a_galerkin + tau * ufl.dot(u, ufl.grad(c)) * ufl.dot(u, ufl.grad(v)) * ufl.dx
    elif method == "gls":
        # For linear elements, ∇·(D∇c) = ∇D·∇c
        res_c = ufl.dot(u, ufl.grad(c)) - ufl.dot(ufl.grad(D), ufl.grad(c))
        res_v = ufl.dot(u, ufl.grad(v)) - ufl.dot(ufl.grad(D), ufl.grad(v))
        a = a_galerkin + tau * res_c * res_v * ufl.dx
    else:
        raise ValueError("Unknown method. Choose 'none', 'supg', or 'gls'.")

    # Boundary conditions: same as forward solve
    inlet1_facets = boundary_data["inlet1"]
    inlet2_facets = boundary_data["inlet2"]
    fdim = msh.topology.dim - 1
    bc_c1 = fem.dirichletbc(PETSc.ScalarType(1.0),
                            fem.locate_dofs_topological(V_conc, fdim, inlet1_facets),
                            V_conc)
    bc_c2 = fem.dirichletbc(PETSc.ScalarType(0.0),
                            fem.locate_dofs_topological(V_conc, fdim, inlet2_facets),
                            V_conc)
    problem = LinearProblem(a, L, bcs=[bc_c1, bc_c2],
                            petsc_options={"ksp_type": "preonly", "pc_type": "lu"}, petsc_options_prefix="lp1_")
    return problem.solve()


def compute_rmse_outlet(c_h, target_expr, boundary_data):
    """RMSE of concentration on outlet vs. target."""
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]
    fdim = V_conc.mesh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x = V_conc.tabulate_dof_coordinates()[dofs]
    y = x[:, 1]
    c_vals = c_h.vector.array[dofs]
    idx = np.argsort(y)
    y = y[idx]; c_vals = c_vals[idx]
    target_vals = target_expr(np.array([np.zeros_like(y), y]))
    return np.sqrt(np.mean((c_vals - target_vals)**2))


def compare_stabilizations(msh, boundary_data, rho_phys, u_h,
                           target_expr, D_fluid=1e-9,
                           methods=["none", "supg", "gls"]):
    """
    Solve convection‑diffusion with multiple stabilisation methods
    and return a dictionary of results (c_h, outlet_rmse).
    """
    results = {}
    for method in methods:
        print(f"  Solving with method: {method}")
        c_h = solve_convection_diffusion(
            msh, boundary_data, rho_phys, u_h,
            D_fluid=D_fluid, method=method
        )
        rmse = compute_rmse_outlet(c_h, target_expr, boundary_data)
        results[method] = {"c_h": c_h, "rmse": rmse}
    return results