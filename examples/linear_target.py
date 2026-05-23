# examples/linear_target.py
from micrograd import GradientGeneratorOptimizer
import matplotlib.pyplot as plt
import numpy as np, os, csv
from dolfinx import fem
import ufl
def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=40, ny=10,
                                     target_expr=lambda x: x[1] / 500e-6,
                                     V_star=0.5)
    rho_phys = opt.run(max_iter=40, beta_continuation=[1,2,4,8,16])
    c_h = opt.c_h
    x = opt.msh.geometry.x
    outlet_facets = opt.boundary_data["outlet"]
    fd = opt.msh.topology.dim - 1
    Vc = c_h.function_space
    dofs = fem.locate_dofs_topological(Vc, fd, outlet_facets)
    y_out = x[dofs, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out)
    y_out, c_out = y_out[idx], c_out[idx]
    rmse = np.sqrt(np.mean((np.clip(c_out, 0, 1) - y_out/500e-6)**2))
    u_h = opt.u_h
    ds_outlet = ufl.Measure("ds", domain=opt.msh,
                            subdomain_data=opt.boundary_data["facet_tag"],
                            subdomain_id=3)
    n = ufl.FacetNormal(opt.msh)
    Q = abs(fem.assemble_scalar(fem.form(ufl.dot(u_h, n) * ds_outlet)))
    R = 1000.0 / Q
    u_mag = np.sqrt(u_h.x.array[::2]**2 + u_h.x.array[1::2]**2)
    U_max = np.max(u_mag)
    with open("figures/metrics_linear.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["outlet_rmse","flow_rate","hydraulic_resistance","max_velocity"])
        w.writerow([rmse, Q, R, U_max])
    plt.figure()
    plt.plot(y_out*1e6, c_out, 'b-', label='Optimised')
    plt.plot([0,500], [0,1], 'k--', label='Target')
    plt.xlabel('y (µm)'); plt.ylabel('Concentration'); plt.legend()
    plt.title('Outlet concentration profile')
    plt.savefig('figures/outlet_profile.pdf'); plt.close()
    print(f"RMSE          = {rmse:.4e}")
    print(f"Hydraulic R   = {R:.4e}  Pa·s/m³")
    print(f"Flow rate Q   = {Q:.4e}  m³/s")
    print(f"Max velocity  = {U_max:.4e}  m/s")
if __name__ == "__main__":
    main()
