# micrograd/validation.py
"""Navier‑Stokes validation, outlet profile utilities, Reynolds number check (FEniCSx ≥ 0.9)."""
import numpy as np
import pyvista as pv
import dolfinx
from dolfinx import fem, mesh, io
from dolfinx.fem.petsc import LinearProblem
from petsc4py import PETSc
import ufl
import basix.ufl
from mpi4py import MPI
import matplotlib.pyplot as plt


def compute_reynolds_number(u_h, rho_fluid=1000.0, mu=1e-3, L_char=None,
                            boundary_data=None):
    """Compute the maximum Reynolds number in the domain."""
    u_mag = np.sqrt(u_h.x.array[::2]**2 + u_h.x.array[1::2]**2)
    U_max = np.max(u_mag)

    if L_char is None and boundary_data is not None:
        L_char = boundary_data.get("Ly", 500e-6) / 2.0
    elif L_char is None:
        L_char = 1e-4

    Re = rho_fluid * U_max * L_char / mu
    if Re > 1.0:
        print(f"⚠️  WARNING: Reynolds number = {Re:.4f} > 1. "
              "Laminar assumption may be invalid.")
    else:
        print(f"✅ Reynolds number = {Re:.4f} << 1. Laminar flow confirmed.")
    return Re


def compute_rmse_outlet(c_h, target_expr, boundary_data):
    """Compute the root‑mean‑square error between the simulated concentration
    at the outlet and the target profile."""
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]
    fdim = V_conc.mesh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)

    x = V_conc.tabulate_dof_coordinates()[dofs]
    y = x[:, 1]
    c_vals = c_h.x.array[dofs]

    idx = np.argsort(y)
    y = y[idx]
    c_vals = c_vals[idx]

    target_vals = target_expr(np.array([np.zeros_like(y), y]))
    rmse = np.sqrt(np.mean((c_vals - target_vals) ** 2))
    return rmse


def plot_outlet_profile(c_h, target_expr, msh, boundary_data,
                        output_file="validation_outlet.png"):
    """Extract and plot the concentration on the outlet boundary."""
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]
    fdim = msh.topology.dim - 1
    dofs_outlet = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x_dofs = V_conc.tabulate_dof_coordinates()
    y_out = x_dofs[dofs_outlet, 1]
    c_out = c_h.x.array[dofs_outlet]

    sort_idx = np.argsort(y_out)
    y_out = y_out[sort_idx]
    c_out = c_out[sort_idx]

    target_vals = target_expr(np.array([np.zeros_like(y_out), y_out]))

    plt.figure(figsize=(6, 4))
    plt.plot(y_out * 1e6, c_out, 'o-', label='Simulation')
    plt.plot(y_out * 1e6, target_vals, 'r--', label='Target')
    plt.xlabel('y (µm)')
    plt.ylabel('Concentration')
    plt.legend()
    plt.title('Outlet concentration validation')
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()

    return y_out, c_out


def threshold_and_extract_fluid_boundary(rho_phys, V_rho, threshold=0.5):
    """Extract ordered boundary points of the fluid region after thresholding."""
    topology, cells, geometry = dolfinx.plot.vtk_mesh(V_rho)
    grid = pv.UnstructuredGrid(cells, geometry, topology)
    grid["density"] = rho_phys.x.array.real

    fluid = grid.threshold(value=threshold, scalars="density", preference="cell")
    if fluid.n_cells == 0:
        raise RuntimeError("No fluid cells found after thresholding.")

    conn = fluid.connectivity(extraction_mode="largest")
    largest = fluid.extract_cells(np.where(conn["RegionId"] == 0)[0])

    boundary = largest.extract_surface()
    if boundary.n_lines == 0:
        raise RuntimeError("Could not extract boundary edges.")

    lines = boundary.lines.reshape(-1, 3)
    points = boundary.points[:, :2]

    adj = {}
    for line in lines:
        i0, i1 = line[1], line[2]
        adj.setdefault(i0, []).append(i1)
        adj.setdefault(i1, []).append(i0)

    ordered = [0]
    visited = {0}
    current = 0
    while len(ordered) < len(points):
        nxt = next((nb for nb in adj[current] if nb not in visited), None)
        if nxt is None:
            nxt = next((i for i in range(len(points)) if i not in visited), None)
            if nxt is None:
                break
        ordered.append(nxt)
        visited.add(nxt)
        current = nxt

    poly_points = points[ordered]
    if not np.allclose(poly_points[0], poly_points[-1]):
        poly_points = np.vstack([poly_points, poly_points[0]])

    return poly_points, boundary


def create_body_fitted_mesh(poly_points, mesh_size=2e-5):
    """Create a 2D mesh from the fluid boundary polygon using Gmsh."""
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    model = gmsh.model
    factory = model.occ

    point_tags = [factory.addPoint(pt[0], pt[1], 0, mesh_size) for pt in poly_points]
    line_tags = [factory.addLine(point_tags[i], point_tags[i + 1])
                 for i in range(len(point_tags) - 1)]
    cl = factory.addCurveLoop(line_tags)
    surf = factory.addPlaneSurface([cl])
    factory.synchronize()

    gmsh.model.mesh.generate(2)
    gmsh.write("temp_validation.msh")

    msh, cell_tags, facet_tags = dolfinx.io.gmshio.read_from_msh(
        "temp_validation.msh", MPI.COMM_SELF, gdim=2)
    gmsh.finalize()

    Lx = np.max(poly_points[:, 0])
    Ly = np.max(poly_points[:, 1])
    tdim = msh.topology.dim
    fdim = tdim - 1

    def left(x): return np.isclose(x[0], 0.0)
    def right(x): return np.isclose(x[0], Lx)
    def top(x): return np.isclose(x[1], Ly)
    def bottom(x): return np.isclose(x[1], 0.0)

    left_facets = mesh.locate_entities_boundary(msh, fdim, left)
    right_facets = mesh.locate_entities_boundary(msh, fdim, right)
    top_facets = mesh.locate_entities_boundary(msh, fdim, top)
    bottom_facets = mesh.locate_entities_boundary(msh, fdim, bottom)

    left_mid = mesh.compute_midpoints(msh, fdim, left_facets)
    y_left = left_mid[:, 1]
    inlet1_facets = left_facets[y_left > Ly / 2]
    inlet2_facets = left_facets[y_left <= Ly / 2]

    facet_indices = np.hstack([inlet1_facets, inlet2_facets, right_facets])
    facet_markers = np.hstack([
        1 * np.ones(len(inlet1_facets), dtype=np.int32),
        2 * np.ones(len(inlet2_facets), dtype=np.int32),
        3 * np.ones(len(right_facets), dtype=np.int32),
    ])
    sorted_idx = np.argsort(facet_indices)
    facet_tag = mesh.meshtags(msh, fdim, facet_indices[sorted_idx], facet_markers[sorted_idx])

    boundary_data = {
        "inlet1": inlet1_facets,
        "inlet2": inlet2_facets,
        "outlet": right_facets,
        "walls": np.hstack([top_facets, bottom_facets]),
        "facet_tag": facet_tag,
        "Lx": Lx,
        "Ly": Ly,
    }
    return msh, boundary_data


def solve_navier_stokes_and_convection(msh, boundary_data, mu=1e-3,
                                      rho_fluid=1000.0, D_fluid=1e-9, P_in=1000.0):
    """Solve steady Navier–Stokes (Picard) + convection‑diffusion on a body‑fitted mesh."""
    P2_vec = basix.ufl.element("Lagrange", msh.topology.cell_name(), 2, shape=(msh.geometry.dim,))
    P1 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 1)
    W_flow = fem.functionspace(msh, basix.ufl.mixed_element([P2_vec, P1]))
    V_conc = fem.functionspace(msh, ("Lagrange", 1))

    inlet1 = boundary_data["inlet1"]
    inlet2 = boundary_data["inlet2"]
    outlet = boundary_data["outlet"]
    walls = boundary_data["walls"]
    fdim = msh.topology.dim - 1

    u_zero = fem.Function(fem.functionspace(msh, P2_vec))
    u_zero.x.array[:] = 0.0
    u_zero.x.scatter_forward()
    bc_walls = fem.dirichletbc(u_zero, fem.locate_dofs_topological(W_flow.sub(0), fdim, walls))
    bc_in1 = fem.dirichletbc(PETSc.ScalarType(P_in), fem.locate_dofs_topological(W_flow.sub(1), fdim, inlet1), W_flow.sub(1))
    bc_in2 = fem.dirichletbc(PETSc.ScalarType(P_in), fem.locate_dofs_topological(W_flow.sub(1), fdim, inlet2), W_flow.sub(1))
    bc_out = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(W_flow.sub(1), fdim, outlet), W_flow.sub(1))
    bcs = [bc_walls, bc_in1, bc_in2, bc_out]

    (u, p) = ufl.TrialFunctions(W_flow)
    (v, q) = ufl.TestFunctions(W_flow)

    # Stokes initial guess (no petsc_options_prefix)
    F_stokes = (mu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
                - p * ufl.div(v) * ufl.dx
                - q * ufl.div(u) * ufl.dx)
    problem = LinearProblem(ufl.lhs(F_stokes), ufl.rhs(F_stokes), bcs=bcs,
                            petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
    w = problem.solve()
    u_prev, p_prev = w.sub(0).collapse(), w.sub(1).collapse()

    # Picard iteration (no petsc_options_prefix)
    for _ in range(5):
        F_ns = (mu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
                + rho_fluid * ufl.inner(ufl.dot(u_prev, ufl.grad(u)), v) * ufl.dx
                - p * ufl.div(v) * ufl.dx
                - q * ufl.div(u) * ufl.dx)
        problem = LinearProblem(ufl.lhs(F_ns), ufl.rhs(F_ns), bcs=bcs,
                                petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
        w = problem.solve()
        u_prev, p_prev = w.sub(0).collapse(), w.sub(1).collapse()
    u_h, p_h = u_prev, p_prev

    # Convection‑diffusion with SUPG (no petsc_options_prefix)
    c = ufl.TrialFunction(V_conc)
    d = ufl.TestFunction(V_conc)
    u_vel = u_h
    h_cell = ufl.CellDiameter(msh)
    u_mag = ufl.sqrt(ufl.dot(u_vel, u_vel) + 1e-20)
    Pe = u_mag * h_cell / (2.0 * D_fluid)
    tau = h_cell / (2.0 * u_mag) * (1.0 / ufl.tanh(Pe) - 1.0 / Pe)

    a_conc = (ufl.dot(u_vel, ufl.grad(c)) * d * ufl.dx
              + D_fluid * ufl.inner(ufl.grad(c), ufl.grad(d)) * ufl.dx
              + tau * ufl.dot(u_vel, ufl.grad(c)) * ufl.dot(u_vel, ufl.grad(d)) * ufl.dx)
    L_conc = fem.Constant(msh, 0.0) * d * ufl.dx

    bc_c1 = fem.dirichletbc(PETSc.ScalarType(1.0), fem.locate_dofs_topological(V_conc, fdim, inlet1), V_conc)
    bc_c2 = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(V_conc, fdim, inlet2), V_conc)
    problem_conc = LinearProblem(a_conc, L_conc, bcs=[bc_c1, bc_c2],
                                 petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
    c_h = problem_conc.solve()

    return u_h, p_h, c_h


def run_navier_stokes_validation(rho_phys, V_rho, target_expr,
                                 output_dir="validation", threshold=0.5, mesh_size=2e-5):
    import os
    os.makedirs(output_dir, exist_ok=True)

    poly_points, _ = threshold_and_extract_fluid_boundary(rho_phys, V_rho, threshold)
    msh_ns, bnd = create_body_fitted_mesh(poly_points, mesh_size)
    u_ns, p_ns, c_ns = solve_navier_stokes_and_convection(msh_ns, bnd)

    y_out, c_out = plot_outlet_profile(
        c_ns, target_expr, msh_ns, bnd,
        output_file=os.path.join(output_dir, "outlet_comparison.png")
    )

    with io.XDMFFile(MPI.COMM_SELF, os.path.join(output_dir, "ns_solution.xdmf"), "w") as xdmf:
        xdmf.write_mesh(msh_ns)
        xdmf.write_function(u_ns, 0)
        xdmf.write_function(c_ns, 1)

    rmse = compute_rmse_outlet(c_ns, target_expr, bnd)
    print(f"Validation RMSE at outlet: {rmse:.5f}")

    return {
        "rmse": rmse,
        "mesh": msh_ns,
        "velocity": u_ns,
        "concentration": c_ns,
        "outlet_y": y_out,
        "outlet_c": c_out,
    }