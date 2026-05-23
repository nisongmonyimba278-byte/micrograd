import numpy as np
from dolfinx import fem
import ufl
from .mesh import create_rectangular_mesh
from .solver import forward_solve
from .adjoint import adjoint_and_sensitivity
from .optimizer import oc_update, mma_update, MMAUpdater
from .utilities import helmholtz_filter, heaviside_projection, alpha
from .compatibility import fallback_to_oc

class GradientGeneratorOptimizer:
    def __init__(self, Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                 target_expr=None, w_f=1e-7, w_c=1.0, V_star=0.5):
        self.Lx, self.Ly = Lx, Ly
        self.msh, self.boundary_data = create_rectangular_mesh(Lx, Ly, nx, ny)
        self.V_rho = fem.functionspace(self.msh, ("Lagrange", 1))
        self.rho = fem.Function(self.V_rho)
        self.rho.x.array[:] = V_star; self.rho.x.scatter_forward()
        self.rho_filt = fem.Function(self.V_rho)
        self.rho_phys = fem.Function(self.V_rho)
        self.target_expr = target_expr or (lambda x: x[1] / self.Ly)
        self.w_f, self.w_c = w_f, w_c
        self.V_star_final = V_star
        self.r_filter = 2 * (Lx / nx)

    def run(self, max_iter=80, beta_continuation=(1,2,4,8,16), move=0.2,
            V_star_schedule=None, method='oc', snapshot_iterations=None):
        method = fallback_to_oc(method)
        if V_star_schedule is None:
            half = max_iter // 2
            V_star_schedule = [(0, 0.7), (half, self.V_star_final)]
        sched = np.array(V_star_schedule)
        V_seq = np.interp(np.arange(max_iter), sched[:,0], sched[:,1])
        history = []
        n_betas = len(beta_continuation); iters_per_beta = max_iter // n_betas
        mma_updater = None
        if method == 'mma':
            mma_updater = MMAUpdater(len(self.rho.x.array), m=1)

        for step in range(max_iter):
            current_V = V_seq[step]
            beta_idx = min(step // iters_per_beta, n_betas - 1)
            beta = beta_continuation[beta_idx]

            helmholtz_filter(self.rho, self.rho_filt, self.V_rho, self.r_filter)
            proj_expr = heaviside_projection(self.rho_filt, beta)
            expr = fem.Expression(proj_expr, self.V_rho.element.interpolation_points())
            self.rho_phys.interpolate(expr)

            u_h, p_h, c_h = forward_solve(self.msh, self.boundary_data, self.rho_phys, P_in=1000.0)
            J, sens_vec = adjoint_and_sensitivity(
                self.msh, self.boundary_data, self.rho_phys, u_h, c_h,
                self.target_expr, w_f=self.w_f, w_c=self.w_c)

            if method == 'oc':
                rho_new = oc_update(self.rho.x.array, sens_vec, self.V_rho, current_V, move=move)
            else:
                rho_new = mma_update(self.rho.x.array, sens_vec, self.V_rho, current_V, mma_updater, move=move)
            self.rho.x.array[:] = rho_new; self.rho.x.scatter_forward()

            history.append((step, beta, J, np.mean(self.rho.x.array)))
            if step % 5 == 0:
                print(f"Iter {step:3d}, β={beta:4.1f}, V*={current_V:.3f}, J={J:.4e}")

        self.history = np.array(history)
        self.u_h, self.c_h = u_h, c_h
        return self.rho_phys

    def plot(self):
        import matplotlib.pyplot as plt, os
        os.makedirs('figures', exist_ok=True)
        plt.figure(); plt.hist(self.rho_phys.x.array, bins=50, color='steelblue', edgecolor='k')
        plt.xlabel('Density ρ'); plt.ylabel('Count')
        plt.title('Final density distribution')
        plt.savefig('figures/density_histogram.pdf'); plt.close()
        print("Density histogram saved to figures/density_histogram.pdf")
