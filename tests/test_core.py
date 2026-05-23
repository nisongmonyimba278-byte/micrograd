# tests/test_core.py
"""Unit tests for micrograd core components (compatible with FEniCSx ≥ 0.9)."""
import numpy as np
import pytest
from dolfinx import fem, mesh, geometry
from mpi4py import MPI
import ufl

from micrograd.mesh import create_rectangular_mesh
from micrograd.solver import forward_solve
from micrograd.adjoint import adjoint_and_sensitivity
from micrograd.utilities import (
    helmholtz_filter,
    alpha,
    alpha_min,
    alpha_max,
    D_min,
    p_simp,
)


# ── Fixtures ───────────────────────────────────────────────
@pytest.fixture
def small_mesh():
    Lx, Ly = 1e-3, 0.5e-3
    msh, bnd_data = create_rectangular_mesh(Lx, Ly, nx=20, ny=10)
    return msh, bnd_data


@pytest.fixture
def density_fluid(small_mesh):
    """Uniform ρ = 1 (pure fluid)."""
    msh, _ = small_mesh
    V_rho = fem.functionspace(msh, ("Lagrange", 1))
    rho = fem.Function(V_rho)
    rho.x.array[:] = 1.0
    rho.x.scatter_forward()
    return rho


# ── 1. Helmholtz filter ────────────────────────────────────
def test_helmholtz_filter(small_mesh):
    msh, _ = small_mesh
    V = fem.functionspace(msh, ("Lagrange", 1))
    rho_in = fem.Function(V)
    x = V.tabulate_dof_coordinates()[:, 0]
    Lx = msh.geometry.x[:, 0].max()
    rho_in.x.array[:] = (x < Lx / 2).astype(np.float64)
    rho_in.x.scatter_forward()

    rho_filt = fem.Function(V)
    r_filter = 1e-4
    helmholtz_filter(rho_in, rho_filt, V, r_filter)

    arr = rho_filt.x.array
    assert np.all(arr >= 0.0) and np.all(arr <= 1.0)
    assert not np.allclose(rho_in.x.array, rho_filt.x.array)


# ── 2. Poiseuille flow validation ──────────────────────────
def test_forward_poiseuille():
    Lx = 2e-3
    Ly = 0.2e-3
    msh = mesh.create_rectangle(MPI.COMM_SELF, [[0.0, 0.0], [Lx, Ly]], [30, 10],
                                cell_type=mesh.CellType.triangle)

    def left(x): return np.isclose(x[0], 0.0)
    def right(x): return np.isclose(x[0], Lx)
    def top(x): return np.isclose(x[1], Ly)
    def bottom(x): return np.isclose(x[1], 0.0)

    fdim = msh.topology.dim - 1
    left_facets = mesh.locate_entities_boundary(msh, fdim, left)
    right_facets = mesh.locate_entities_boundary(msh, fdim, right)
    top_facets = mesh.locate_entities_boundary(msh, fdim, top)
    bottom_facets = mesh.locate_entities_boundary(msh, fdim, bottom)

    facet_indices = np.hstack([left_facets, right_facets])
    facet_markers = np.hstack([
        1 * np.ones(len(left_facets), dtype=np.int32),
        3 * np.ones(len(right_facets), dtype=np.int32),
    ])
    sorted_idx = np.argsort(facet_indices)
    facet_tag = mesh.meshtags(msh, fdim, facet_indices[sorted_idx], facet_markers[sorted_idx])

    boundary_data = {
        "inlet1": left_facets,
        "inlet2": np.array([], dtype=np.int32),
        "outlet": right_facets,
        "walls": np.hstack([top_facets, bottom_facets]),
        "facet_tag": facet_tag,
        "Lx": Lx, "Ly": Ly,
    }

    V_rho = fem.functionspace(msh, ("Lagrange", 1))
    rho = fem.Function(V_rho)
    rho.x.array[:] = 1.0
    rho.x.scatter_forward()

    P_in = 1000.0
    mu = 1e-3
    u_h, p_h, _ = forward_solve(msh, boundary_data, rho, mu=mu, P_in=P_in)

    h = Ly
    deltaP = P_in
    U_scale = deltaP / (2 * mu * Lx)
    y_coords = msh.geometry.x[:, 1]
    u_analytical = U_scale * y_coords * (h - y_coords)

    # Evaluate at x = Lx/2
    x_mid = Lx / 2
    bb_tree = geometry.BoundingBoxTree(msh, msh.topology.dim)
    points = np.array([[x_mid, yi, 0.0] for yi in np.linspace(0, h, 30)])
    cells = []
    for pt in points:
        cell = bb_tree.compute_first_entity_collision(pt)
        cells.append(cell if cell is not None else -1)

    u_values = u_h.eval(points, cells)
    u_x_num = u_values[:, 0]
    y_pts = points[:, 1]
    u_x_ana = U_scale * y_pts * (h - y_pts)

    mask = (y_pts > 0.1 * h) & (y_pts < 0.9 * h)
    rel_error = np.max(np.abs(u_x_num[mask] - u_x_ana[mask]) / (U_scale * (h**2 / 4) + 1e-12))
    assert rel_error < 0.05, f"Poiseuille error too large: {rel_error}"


# ── 3. Adjoint sensitivity (finite‑difference check) ───────
def test_adjoint_sensitivity(small_mesh, density_fluid):
    msh, bnd = small_mesh
    rho = density_fluid
    V_rho = rho.function_space
    Ly = bnd["Ly"]
    target_expr = lambda x: x[1] / Ly
    w_f = 1e-7
    w_c = 1.0

    u_h, p_h, c_h = forward_solve(msh, bnd, rho)
    J, sens_vec = adjoint_and_sensitivity(msh, bnd, rho, u_h, c_h, target_expr,
                                          w_f=w_f, w_c=w_c)
    sens_adj = sens_vec.array.copy()

    n_test = 5
    np.random.seed(42)
    dof_indices = np.random.choice(len(sens_adj), n_test, replace=False)
    eps = 1e-6

    fd_grad = np.zeros(n_test)
    for i, dof in enumerate(dof_indices):
        rho_pert = fem.Function(V_rho)
        rho_pert.x.array[:] = rho.x.array.copy()
        rho_pert.x.array[dof] += eps
        rho_pert.x.scatter_forward()

        u_p, p_p, c_p = forward_solve(msh, bnd, rho_pert)
        J_f = fem.assemble_scalar(fem.form(
            0.5 * 1e-3 * ufl.inner(ufl.grad(u_p), ufl.grad(u_p)) * ufl.dx
            + 0.5 * alpha(rho_pert) * ufl.inner(u_p, u_p) * ufl.dx
        ))
        target_fn = fem.Function(c_p.function_space)
        target_fn.interpolate(target_expr)
        ds_outlet = ufl.Measure("ds", domain=msh, subdomain_data=bnd["facet_tag"], subdomain_id=3)
        J_c = fem.assemble_scalar(fem.form(0.5 * (c_p - target_fn) ** 2 * ds_outlet))
        J_pert = w_f * J_f + w_c * J_c
        fd_grad[i] = (J_pert - J) / eps

    rel_errors = np.abs(sens_adj[dof_indices] - fd_grad) / (np.abs(fd_grad) + 1e-12)
    max_rel_err = np.max(rel_errors)
    assert max_rel_err < 0.01, f"Adjoint sensitivity mismatch, max rel error = {max_rel_err}"