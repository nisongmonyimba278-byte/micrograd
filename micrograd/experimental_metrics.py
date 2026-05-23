# micrograd/experimental_metrics.py (updated)
import numpy as np
from dolfinx import fem
import ufl
from scipy.ndimage import distance_transform_edt
from scipy.interpolate import griddata

def compute_metrics(msh, boundary_data, rho_phys, u_h, c_h, target_expr,
                    mu=1e-3, rho_fluid=1000.0, D_fluid=1e-9,
                    threshold=0.5, num_x_slices=20):
    P_in = 1000.0; delta_P = P_in
    ds_outlet = ufl.Measure("ds", domain=msh, subdomain_data=boundary_data["facet_tag"], subdomain_id=3)
    n = ufl.FacetNormal(msh)
    Q = abs(fem.assemble_scalar(fem.form(ufl.dot(u_h, n) * ds_outlet)))
    R_hyd = delta_P / Q if Q > 1e-20 else np.inf

    u_mag = np.sqrt(u_h.x.array[::2]**2 + u_h.x.array[1::2]**2)
    U_max = np.max(u_mag)

    V_rho = rho_phys.function_space
    rho_binary = (rho_phys.x.array > threshold).astype(int)
    pts = V_rho.tabulate_dof_coordinates()[:,:2]
    Lx, Ly = msh.geometry.x[:,0].max(), msh.geometry.x[:,1].max()
    res = 1e-6; nx = int(Lx/res)+1; ny = int(Ly/res)+1
    x_grid = np.linspace(0, Lx, nx); y_grid = np.linspace(0, Ly, ny)
    X, Y = np.meshgrid(x_grid, y_grid)
    binary_grid = griddata(pts, rho_binary, (X, Y), method='nearest', fill_value=0)
    dist = distance_transform_edt(binary_grid == 1)
    if np.any(binary_grid == 1):
        min_dist = dist[binary_grid == 1].min()
        min_width = 2 * min_dist * res
        avg_width = 2 * np.mean(dist[binary_grid == 1]) * res
    else:
        min_width = avg_width = 0.0
    L_char = avg_width if avg_width > 0 else (Ly/2)

    Re = rho_fluid * U_max * L_char / mu
    Pe = U_max * L_char / D_fluid

    x_all = msh.geometry.x[:,0]; y_all = msh.geometry.x[:,1]
    c_vals = c_h.x.array; target_vals = target_expr(np.array([x_all, y_all]))
    diff = (c_vals - target_vals)**2
    bin_edges = np.linspace(0, Lx, 50); bin_centers = (bin_edges[:-1]+bin_edges[1:])/2
    error_profile = np.array([np.mean(diff[(x_all>=e0)&(x_all<e1)]) if np.any((x_all>=e0)&(x_all<e1)) else np.nan
                              for e0,e1 in zip(bin_edges[:-1], bin_edges[1:])])
    thresh = 0.05 * 1.0**2
    mix_len = Lx
    for i, err in enumerate(error_profile):
        if err < thresh: mix_len = bin_centers[i]; break

    fluid_area = fem.assemble_scalar(fem.form(rho_binary * ufl.dx))

    # outlet RMSE
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]; fdim = msh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    y_out = V_conc.tabulate_dof_coordinates()[dofs, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_out = y_out[idx]; c_out = c_out[idx]
    target_out = target_expr(np.array([np.zeros_like(y_out), y_out]))
    outlet_rmse = np.sqrt(np.mean((c_out - target_out)**2))

    return {
        "pressure_drop_Pa": delta_P,
        "total_flow_rate_m3_per_s": Q,
        "hydraulic_resistance_Pa_s_per_m3": R_hyd,
        "max_velocity_m_per_s": U_max,
        "characteristic_length_m": L_char,
        "Reynolds_number": Re,
        "Peclet_number": Pe,
        "mixing_length_m": mix_len,
        "min_feature_size_m": min_width,
        "total_fluid_volume_m3": fluid_area,
        "outlet_rmse": outlet_rmse,
    }