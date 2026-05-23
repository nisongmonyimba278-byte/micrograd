# micrograd/christmas_tree.py (updated)
import numpy as np
from dolfinx import fem
from .solver import forward_solve

def _tree_segments(Lx=2000e-6, Ly=500e-6, channel_width=10e-6):
    segs = [
        (0.0, 50e-6, 400e-6, 50e-6),
        (0.0, 150e-6, 400e-6, 150e-6),
        (0.0, 250e-6, 400e-6, 250e-6),
        (0.0, 350e-6, 400e-6, 350e-6),
        (0.0, 450e-6, 400e-6, 450e-6),
        (400e-6, 50e-6,  800e-6, 100e-6),
        (400e-6, 150e-6, 800e-6, 100e-6),
        (400e-6, 150e-6, 800e-6, 200e-6),
        (400e-6, 250e-6, 800e-6, 200e-6),
        (400e-6, 250e-6, 800e-6, 300e-6),
        (400e-6, 350e-6, 800e-6, 300e-6),
        (400e-6, 350e-6, 800e-6, 400e-6),
        (400e-6, 450e-6, 800e-6, 400e-6),
        (800e-6, 100e-6, 1200e-6, 125e-6),
        (800e-6, 200e-6, 1200e-6, 125e-6),
        (800e-6, 200e-6, 1200e-6, 250e-6),
        (800e-6, 300e-6, 1200e-6, 250e-6),
        (800e-6, 300e-6, 1200e-6, 375e-6),
        (800e-6, 400e-6, 1200e-6, 375e-6),
        (1200e-6, 125e-6, 1600e-6, 150e-6),
        (1200e-6, 250e-6, 1600e-6, 150e-6),
        (1200e-6, 250e-6, 1600e-6, 350e-6),
        (1200e-6, 375e-6, 1600e-6, 350e-6),
        (1600e-6, 150e-6, 2000e-6, 150e-6),
        (1600e-6, 150e-6, 2000e-6, 250e-6),
        (1600e-6, 350e-6, 2000e-6, 250e-6),
        (1600e-6, 350e-6, 2000e-6, 350e-6),
    ]
    return segs

def create_christmas_tree_density(msh, Lx=2000e-6, Ly=500e-6, num_inlets=5, channel_width=10e-6):
    V_rho = fem.functionspace(msh, ("Lagrange", 1))
    rho = fem.Function(V_rho)
    rho.x.array[:] = 0.0; rho.x.scatter_forward()
    x_coords = V_rho.tabulate_dof_coordinates(); x = x_coords[:,0]; y = x_coords[:,1]
    segments = _tree_segments(Lx, Ly, channel_width)
    half_w = channel_width / 2.0
    inside = np.zeros(len(x), dtype=bool)
    for (x0, y0, x1, y1) in segments:
        dx = x1 - x0; dy = y1 - y0; len2 = dx*dx + dy*dy
        if len2 < 1e-20:
            dist = np.sqrt((x - x0)**2 + (y - y0)**2)
        else:
            t = ((x - x0)*dx + (y - y0)*dy) / len2; t = np.clip(t, 0.0, 1.0)
            proj_x = x0 + t*dx; proj_y = y0 + t*dy
            dist = np.sqrt((x - proj_x)**2 + (y - proj_y)**2)
        inside |= (dist < half_w)
    rho.x.array[inside] = 1.0; rho.x.scatter_forward()
    return rho

def simulate_christmas_tree(msh, boundary_data, rho_tree, target_expr):
    from dolfinx import fem; import ufl; from .utilities import alpha
    u_h, p_h, c_h = forward_solve(msh, boundary_data, rho_tree)
    mu = 1e-3
    J_f = fem.assemble_scalar(fem.form(
        0.5 * mu * ufl.inner(ufl.grad(u_h), ufl.grad(u_h)) * ufl.dx
        + 0.5 * alpha(rho_tree) * ufl.inner(u_h, u_h) * ufl.dx
    ))
    V_conc = c_h.function_space; outlet_facets = boundary_data["outlet"]; fdim = msh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x_coords = V_conc.tabulate_dof_coordinates()[dofs]; y_out = x_coords[:,1]; c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_out = y_out[idx]; c_out = c_out[idx]
    target_vals = target_expr(np.array([np.zeros_like(y_out), y_out]))
    rmse = np.sqrt(np.mean((c_out - target_vals)**2))
    return {"velocity": u_h, "pressure": p_h, "concentration": c_h, "dissipation": J_f, "outlet_rmse": rmse, "outlet_y": y_out, "outlet_c": c_out}