# micrograd/validation_3d.py (compatible with dolfinx v0.7.3)
import numpy as np, pyvista as pv, gmsh, dolfinx, ufl, basix.ufl
from dolfinx import fem, mesh, io
from dolfinx.fem.petsc import LinearProblem
from petsc4py import PETSc
from mpi4py import MPI
import matplotlib.pyplot as plt
from .validation import threshold_and_extract_fluid_boundary

def extrude_and_mesh_3d(rho_phys, V_rho, threshold=0.5, height=100e-6, mesh_size=1e-4):
    poly_points_2d, _ = threshold_and_extract_fluid_boundary(rho_phys, V_rho, threshold)
    if not np.allclose(poly_points_2d[0], poly_points_2d[-1]):
        poly_points_2d = np.vstack([poly_points_2d, poly_points_2d[0]])

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    model = gmsh.model; factory = model.occ
    base_points = [factory.addPoint(pt[0], pt[1], 0, mesh_size) for pt in poly_points_2d]
    lines = [factory.addLine(base_points[i], base_points[i+1]) for i in range(len(base_points)-1)]
    cl = factory.addCurveLoop(lines); base_surf = factory.addPlaneSurface([cl])
    extruded = factory.extrude([(2, base_surf)], 0, 0, height)
    factory.synchronize()
    model.addPhysicalGroup(3, [extruded[1][0]])
    gmsh.model.mesh.generate(3)
    gmsh.write("temp_3d.msh")
    msh, cell_tags, facet_tags = dolfinx.io.gmshio.read_from_msh("temp_3d.msh", MPI.COMM_SELF, gdim=3)
    gmsh.finalize()

    Lx = np.max(poly_points_2d[:,0]); Ly = np.max(poly_points_2d[:,1])
    tdim = msh.topology.dim; fdim = tdim - 1
    def left(x): return np.isclose(x[0], 0.0)
    def right(x): return np.isclose(x[0], Lx)
    def top_y(x): return np.isclose(x[1], Ly)
    def bottom_y(x): return np.isclose(x[1], 0.0)
    def bottom_z(x): return np.isclose(x[2], 0.0)
    def top_z(x): return np.isclose(x[2], height)
    left_facets = mesh.locate_entities_boundary(msh, fdim, left)
    right_facets = mesh.locate_entities_boundary(msh, fdim, right)
    top_y_facets = mesh.locate_entities_boundary(msh, fdim, top_y)
    bottom_y_facets = mesh.locate_entities_boundary(msh, fdim, bottom_y)
    bottom_z_facets = mesh.locate_entities_boundary(msh, fdim, bottom_z)
    top_z_facets = mesh.locate_entities_boundary(msh, fdim, top_z)
    left_mid = mesh.compute_midpoints(msh, fdim, left_facets); y_left = left_mid[:,1]
    inlet1_facets = left_facets[y_left > Ly/2]; inlet2_facets = left_facets[y_left <= Ly/2]
    walls_facets = np.hstack([top_y_facets, bottom_y_facets, top_z_facets, bottom_z_facets])
    facet_indices = np.hstack([inlet1_facets, inlet2_facets, right_facets])
    facet_markers = np.hstack([1*np.ones(len(inlet1_facets), dtype=np.int32),
                               2*np.ones(len(inlet2_facets), dtype=np.int32),
                               3*np.ones(len(right_facets), dtype=np.int32)])
    sorted_idx = np.argsort(facet_indices); facet_tag = mesh.meshtags(msh, fdim, facet_indices[sorted_idx], facet_markers[sorted_idx])
    boundary_data = {"inlet1": inlet1_facets, "inlet2": inlet2_facets, "outlet": right_facets,
                     "walls": walls_facets, "facet_tag": facet_tag, "Lx": Lx, "Ly": Ly, "height": height}
    return msh, boundary_data

def solve_3d_navier_stokes_convection(msh, boundary_data, mu=1e-3, rho_fluid=1000.0, D_fluid=1e-9, P_in=1000.0):
    P2_vec = basix.ufl.element("Lagrange", msh.topology.cell_name(), 2, shape=(msh.geometry.dim,))
    P1 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 1)
    W_flow = fem.functionspace(msh, basix.ufl.mixed_element([P2_vec, P1]))
    V_conc = fem.functionspace(msh, ("Lagrange", 1))
    inlet1 = boundary_data["inlet1"]; inlet2 = boundary_data["inlet2"]
    outlet = boundary_data["outlet"]; walls = boundary_data["walls"]
    fdim = msh.topology.dim - 1
    u_zero = fem.Function(fem.functionspace(msh, P2_vec))
    u_zero.x.array[:] = 0.0; u_zero.x.scatter_forward()
    bc_walls = fem.dirichletbc(u_zero, fem.locate_dofs_topological(W_flow.sub(0), fdim, walls))
    bc_in1 = fem.dirichletbc(PETSc.ScalarType(P_in), fem.locate_dofs_topological(W_flow.sub(1), fdim, inlet1), W_flow.sub(1))
    bc_in2 = fem.dirichletbc(PETSc.ScalarType(P_in), fem.locate_dofs_topological(W_flow.sub(1), fdim, inlet2), W_flow.sub(1))
    bc_out = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(W_flow.sub(1), fdim, outlet), W_flow.sub(1))
    bcs = [bc_walls, bc_in1, bc_in2, bc_out]
    (u, p) = ufl.TrialFunctions(W_flow); (v, q) = ufl.TestFunctions(W_flow)
    F_stokes = (mu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx - p * ufl.div(v) * ufl.dx - q * ufl.div(u) * ufl.dx)
    # Removed petsc_options_prefix from all LinearProblem calls
    problem = LinearProblem(ufl.lhs(F_stokes), ufl.rhs(F_stokes), bcs=bcs,
                            petsc_options_prefix="lp9_", petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
    w = problem.solve(); u_prev, p_prev = w.sub(0).collapse(), w.sub(1).collapse()
    for _ in range(4):
        F_ns = (mu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
                + rho_fluid * ufl.inner(ufl.dot(u_prev, ufl.grad(u)), v) * ufl.dx
                - p * ufl.div(v) * ufl.dx - q * ufl.div(u) * ufl.dx)
        problem = LinearProblem(ufl.lhs(F_ns), ufl.rhs(F_ns), bcs=bcs,
                                petsc_options_prefix="lp10_", petsc_options={"ksp_type": "preonly", "pc_type": "lu"})
        w = problem.solve(); u_prev, p_prev = w.sub(0).collapse(), w.sub(1).collapse()
    u_h, p_h = u_prev, p_prev
    c = ufl.TrialFunction(V_conc); d = ufl.TestFunction(V_conc); u_vel = u_h
    h = ufl.CellDiameter(msh); u_mag = ufl.sqrt(ufl.dot(u_vel, u_vel) + 1e-20)
    Pe = u_mag * h / (2.0 * D_fluid); tau = h / (2.0 * u_mag) * (1.0 / ufl.tanh(Pe) - 1.0 / Pe)
    a_conc = (ufl.dot(u_vel, ufl.grad(c)) * d * ufl.dx + D_fluid * ufl.inner(ufl.grad(c), ufl.grad(d)) * ufl.dx
              + tau * ufl.dot(u_vel, ufl.grad(c)) * ufl.dot(u_vel, ufl.grad(d)) * ufl.dx)
    L_conc = fem.Constant(msh, 0.0) * d * ufl.dx
    bc_c1 = fem.dirichletbc(PETSc.ScalarType(1.0), fem.locate_dofs_topological(V_conc, fdim, inlet1), V_conc)
    bc_c2 = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(V_conc, fdim, inlet2), V_conc)
    problem_conc = LinearProblem(a_conc, L_conc, bcs=[bc_c1, bc_c2],
                                 petsc_options_prefix="lp11_", petsc_options={"ksp_type": "preonly", "pc_type": "lu"}, petsc_options_prefix="lp1_")
    c_h = problem_conc.solve()
    return u_h, p_h, c_h

def plot_3d_outlet_and_render(msh, c_h, boundary_data, target_expr, output_dir="3d_validation"):
    import os; os.makedirs(output_dir, exist_ok=True)
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]; fdim = msh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x = V_conc.tabulate_dof_coordinates()[dofs]; y = x[:,1]; c_vals = c_h.x.array[dofs]
    y_unique = np.unique(np.round(y, 8)); c_mean = np.array([c_vals[np.isclose(y, yv, atol=1e-6)].mean() for yv in y_unique])
    c_target = target_expr(np.array([np.zeros_like(y_unique), y_unique]))
    plt.figure(); plt.plot(y_unique*1e6, c_mean, 'o-', label='3D'); plt.plot(y_unique*1e6, c_target, 'r--', label='Target')
    plt.xlabel('y (µm)'); plt.ylabel('Concentration'); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "3d_outlet_profile.png")); plt.close()
    topology, cells, geometry = dolfinx.plot.vtk_mesh(msh)
    grid = pv.UnstructuredGrid(cells, geometry, topology)
    grid.point_data["concentration"] = c_h.x.array.real
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(grid, cmap="coolwarm", show_edges=False, clim=[0,1]); plotter.view_zy()
    plotter.screenshot(os.path.join(output_dir, "3d_render.png")); plotter.close()
    rmse = np.sqrt(np.mean((c_mean - c_target)**2))
    return rmse

def run_full_3d_validation(rho_phys_2d, V_rho_2d, target_expr, output_dir="3d_validation", height=100e-6, mesh_size=5e-5):
    msh_3d, bnd = extrude_and_mesh_3d(rho_phys_2d, V_rho_2d, height=height, mesh_size=mesh_size)
    u_h, p_h, c_h = solve_3d_navier_stokes_convection(msh_3d, bnd, P_in=1000.0)
    rmse = plot_3d_outlet_and_render(msh_3d, c_h, bnd, target_expr, output_dir=output_dir)
    print(f"3D validation RMSE: {rmse:.5f}")
    with io.XDMFFile(MPI.COMM_SELF, f"{output_dir}/solution_3d.xdmf", "w") as f:
        f.write_mesh(msh_3d); f.write_function(u_h, 0); f.write_function(c_h, 1)
    return rmse
