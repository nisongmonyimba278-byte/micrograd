from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, os, csv
from dolfinx import fem
import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=20, ny=5,
        target_expr=lambda x: x[1] / 500e-6,
        w_f=1e-7, w_c=5e4, V_star=0.5)
    # sinusoidal init already applied inside GradientGeneratorOptimizer.__init__
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)

    c_h = opt.c_h
    outlet_facets = opt.boundary_data["outlet"]
    ft = opt.boundary_data["facet_tag"]
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, outlet_facets)
    y_out = opt.msh.geometry.x[dofs, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out)
    y_s, c_s = y_out[idx], c_out[idx]
    Ly = 500e-6

    fig, ax = plt.subplots()
    ax.plot(y_s * 1e6, c_s, 'b-', label='TopOpt')
    ax.plot(y_s * 1e6, y_s / Ly, 'r--', label='Target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/outlet_profile.pdf', bbox_inches='tight')
    plt.close()

    u_h = opt.u_h
    ds_out = ufl.Measure("ds", domain=opt.msh, subdomain_data=ft, subdomain_id=3)
    n = ufl.FacetNormal(opt.msh)
    Q = float(abs(fem.assemble_scalar(fem.form(ufl.dot(u_h, n) * ds_out))))
    R = 1000.0 / Q if Q > 1e-30 else float('inf')
    rmse = float(np.sqrt(np.mean((np.clip(c_s, 0, 1) - y_s / Ly) ** 2)))
    U_max = float(np.max(np.sqrt(u_h.x.array[::2]**2 + u_h.x.array[1::2]**2)))

    print(f"RMSE          = {rmse:.4e}")
    print(f"Hydraulic R   = {R:.4e}  Pa·s/m³")
    print(f"Flow rate Q   = {Q:.4e}  m³/s")
    print(f"Max velocity  = {U_max:.4e}  m/s")

    with open('figures/metrics_linear.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Metric', 'Value'])
        w.writerow(['RMSE', rmse])
        w.writerow(['Hydraulic R (Pa.s/m^3)', R])
        w.writerow(['Flow rate (m^3/s)', Q])
        w.writerow(['Max velocity (m/s)', U_max])

if __name__ == '__main__':
    main()
