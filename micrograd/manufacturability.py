# micrograd/manufacturability.py (updated)
import numpy as np, matplotlib.pyplot as plt
try:
    from scipy.ndimage import distance_transform_edt
    from scipy.interpolate import griddata
except ImportError:
    distance_transform_edt = None
    griddata = None

def measure_min_feature_size(rho_phys, V_rho, threshold=0.5, resolution=1e-6,
                             plot_distribution=False, output_file=None):
    fab_limit_um = 10.0; fab_limit_m = fab_limit_um*1e-6
    pts = V_rho.tabulate_dof_coordinates()[:,:2]
    vals = (rho_phys.x.array > threshold).astype(np.float64)
    x_min, y_min = pts.min(axis=0); x_max, y_max = pts.max(axis=0)
    nx = int((x_max-x_min)/resolution)+1; ny = int((y_max-y_min)/resolution)+1
    x_grid = np.linspace(x_min, x_max, nx); y_grid = np.linspace(y_min, y_max, ny)
    X, Y = np.meshgrid(x_grid, y_grid)
    binary_grid = griddata(pts, vals, (X, Y), method='nearest', fill_value=0.0)
    dist_pixels = distance_transform_edt(binary_grid==1); dist_m = dist_pixels * resolution
    fluid_mask = binary_grid==1
    if not np.any(fluid_mask): return {"min_width_m":0.0, "avg_width_m":0.0, "min_width_um":0.0, "avg_width_um":0.0, "fab_ok":False, "fab_limit_um":fab_limit_um}
    min_width = 2 * dist_m[fluid_mask].min(); avg_width = 2 * np.mean(dist_m[fluid_mask])
    ok = min_width >= fab_limit_m
    if plot_distribution:
        plt.figure(); widths_um = 2 * dist_m[fluid_mask] * 1e6
        plt.hist(widths_um, bins=50, alpha=0.7, color='steelblue')
        plt.axvline(fab_limit_um, color='r', linestyle='--', label=f'Fab limit ({fab_limit_um} µm)')
        plt.axvline(min_width*1e6, color='k', linestyle=':', label=f'Min width = {min_width*1e6:.1f} µm')
        plt.xlabel('Channel width [µm]'); plt.ylabel('Count'); plt.legend(); plt.title('Channel width distribution')
        if output_file: plt.savefig(output_file, dpi=150)
        plt.close()
    return {"min_width_m":min_width, "avg_width_m":avg_width, "min_width_um":min_width*1e6, "avg_width_um":avg_width*1e6, "fab_ok":ok, "fab_limit_um":fab_limit_um}

def robust_projection(rho_filt, beta, eta_d, V_rho):
    import ufl; from dolfinx import fem
    def heaviside(rho, beta, eta):
        return (ufl.tanh(beta*eta) + ufl.tanh(beta*(rho-eta))) / (ufl.tanh(beta*eta) + ufl.tanh(beta*(1.0-eta)))
    eroded_expr = heaviside(rho_filt, beta, eta_d)
    nominal_expr = heaviside(rho_filt, beta, 0.5)
    dilated_expr = heaviside(rho_filt, beta, 1.0-eta_d)
    eroded, nominal, dilated = fem.Function(V_rho), fem.Function(V_rho), fem.Function(V_rho)
    eroded.interpolate(lambda x: np.clip(eroded_expr.eval(x), 0, 1))
    nominal.interpolate(lambda x: np.clip(nominal_expr.eval(x), 0, 1))
    dilated.interpolate(lambda x: np.clip(dilated_expr.eval(x), 0, 1))
    return eroded, nominal, dilated