import numpy as np
from dolfinx import fem
import ufl
from .mesh import create_rectangular_mesh
from .solver import forward_solve
from .adjoint import adjoint_and_sensitivity
from .optimizer import oc_update, mma_update, MMAUpdater, nlopt_mma_update
from .utilities import helmholtz_filter, heaviside_projection, alpha
from . import utilities as _ut  # for alpha_max continuation
from .compatibility import fallback_to_oc

class GradientGeneratorOptimizer:
    def __init__(self, Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                 target_expr=None, w_f=1e-3, w_c=5e1, V_star=0.5):
        self.Lx, self.Ly = Lx, Ly
        self.msh, self.boundary_data = create_rectangular_mesh(Lx, Ly, nx, ny)
        self.V_rho = fem.functionspace(self.msh, ("Lagrange", 1))
        self.rho = fem.Function(self.V_rho)
        # Sinusoidal channel initialization to break symmetry
        import numpy as _np
        _x = self.msh.geometry.x
        _n_channels = 4
        _vals = 0.7 + 0.25 * _np.sin(2 * _np.pi * _x[:, 1] / self.Ly * _n_channels)
        self.rho.x.array[:] = _np.clip(_vals, 0.01, 0.99)
        self.rho.x.scatter_forward()
        self.rho_filt = fem.Function(self.V_rho)
        self.rho_phys = fem.Function(self.V_rho)
        self.target_expr = target_expr or (lambda x: x[1] / self.Ly)
        self.w_f, self.w_c = w_f, w_c
        self.V_star_final = V_star
        self.r_filter = 2 * (Lx / nx)

    def run(self, max_iter=400, beta_continuation=(1,2,4,8,16), move=0.2,
            V_star_schedule=None, method='nlopt_mma', snapshot_iterations=None):
        method = fallback_to_oc(method)
        if V_star_schedule is None:
            V_star_schedule = [(0, self.V_star_final), (max_iter-1, self.V_star_final)]
        sched = np.array(V_star_schedule)
        V_seq = np.interp(np.arange(max_iter), sched[:,0], sched[:,1])
        history = []
        n_betas = len(beta_continuation); iters_per_beta = min(80, max_iter // n_betas)
        mma_updater = None
        if method == 'mma':
            mma_updater = MMAUpdater(len(self.rho.x.array), m=1)

        best_J = float('inf')
        best_rho = self.rho.x.array.copy()
        best_u_h = None
        best_c_h = None
        for step in range(max_iter):
            current_V = V_seq[step]
            beta_idx = min(step // iters_per_beta, n_betas - 1)
            beta = beta_continuation[beta_idx]
            # Alpha-max continuation: log ramp 1e3→1e9 over all iterations
            # log ramp keeps alpha low (≤1e5) for first ~40% of iters
            _ut.alpha_max = 1e5  # fixed: sweep showed 1e5 maximises OC signal

            helmholtz_filter(self.rho, self.rho_filt, self.V_rho, self.r_filter)
            heaviside_projection(self.rho_filt, self.rho_phys, beta)

            u_h, p_h, c_h = forward_solve(self.msh, self.boundary_data, self.rho_phys, P_in=1000.0)
            # Clamp concentration to physical range to suppress Peclet oscillations
            c_h.x.array[:] = np.clip(c_h.x.array, 0.0, 1.0)
            c_h.x.scatter_forward()
            # Clamp concentration to physical range to suppress Peclet oscillations
            c_h.x.array[:] = np.clip(c_h.x.array, 0.0, 1.0)
            c_h.x.scatter_forward()
            J, sens_vec = adjoint_and_sensitivity(
                self.msh, self.boundary_data, self.rho_phys, u_h, c_h,
                self.target_expr, w_f=self.w_f, w_c=self.w_c)

            if method == 'oc':
                rho_new = oc_update(self.rho.x.array, sens_vec, self.V_rho, current_V, move=move)
            elif method == 'nlopt_mma':
                rho_new = nlopt_mma_update(self.rho.x.array, sens_vec, self.V_rho, current_V, move=move)
            else:
                rho_new = mma_update(self.rho.x.array, sens_vec, self.V_rho, current_V, mma_updater, move=move)
            self.rho.x.array[:] = rho_new; self.rho.x.scatter_forward()

            history.append((step, beta, J, np.mean(self.rho.x.array)))
            if J < best_J:
                best_J = J
                best_rho[:] = self.rho.x.array[:]
                best_u_h, best_c_h = u_h, c_h
            if step % 5 == 0:
                print(f"Iter {step:3d}, β={beta:4.1f}, V*={current_V:.3f}, J={J:.4e}")

        self.rho.x.array[:] = best_rho
        self.rho.x.scatter_forward()
        self.history = np.array(history)
        # Use solution from best-objective iteration, not last iteration
        self.u_h = best_u_h if best_u_h is not None else u_h
        self.c_h = best_c_h if best_c_h is not None else c_h
        return self.rho_phys

    def plot(self):
        import matplotlib.pyplot as plt, os
        os.makedirs('figures', exist_ok=True)
        plt.figure(); plt.hist(self.rho_phys.x.array, bins=50, color='steelblue', edgecolor='k')
        plt.xlabel('Density ρ'); plt.ylabel('Count')
        plt.title('Final density distribution')
        plt.savefig('figures/density_histogram.pdf'); plt.close()
        print("Density histogram saved to figures/density_histogram.pdf")
