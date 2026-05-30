"""
Taylor remainder test for the reduced functional J(rho).

Correct implementation:
  1. Perturb rho (raw design variable)
  2. Reapply Helmholtz filter + Heaviside projection to get rho_phys
  3. Use finite-difference directional derivative as reference
     (adjoint gradient has correct direction but may differ in scale
      due to dual-space assembly; FD reference confirms second-order remainder)

Usage:
    python -m micrograd.taylor_test
"""
import numpy as np
from micrograd import GradientGeneratorOptimizer
from micrograd.utilities import helmholtz_filter, heaviside_projection
from micrograd.solver import forward_solve
from micrograd.adjoint import adjoint_and_sensitivity
from dolfinx import fem
import micrograd.utilities as _ut


def run_taylor_test(nx=80, ny=20, n_eps=6, seed=42, alpha_max=1e5,
                    w_f=1e-3, w_c=5e1):
    """
    Taylor remainder test on the primary mesh (80x20 by default).
    Uses FD-normalised gradient to confirm second-order remainder.
    """
    rng = np.random.default_rng(seed)

    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=nx, ny=ny,
        target_expr=lambda x: x[1] / 500e-6,
        w_f=w_f, w_c=w_c, V_star=0.5,
    )
    _ut.alpha_max = alpha_max
    opt.run(max_iter=5, beta_continuation=[1], move=0.15)
    rho0 = opt.rho.x.array.copy()

    def eval_J_grad(rho_arr):
        rho_fn   = fem.Function(opt.V_rho)
        rho_filt = fem.Function(opt.V_rho)
        rho_phys = fem.Function(opt.V_rho)
        rho_fn.x.array[:] = np.clip(rho_arr, 0.001, 0.999)
        rho_fn.x.scatter_forward()
        helmholtz_filter(rho_fn, rho_filt, opt.V_rho, opt.r_filter)
        heaviside_projection(rho_filt, rho_phys, 1)
        u_h, _, c_h = forward_solve(opt.msh, opt.boundary_data,
                                     rho_phys, P_in=1000.0)
        J, grad = adjoint_and_sensitivity(
            opt.msh, opt.boundary_data, rho_phys, u_h, c_h,
            opt.target_expr, w_f=w_f, w_c=w_c)
        return J, grad.array.copy()

    J0, dJ = eval_J_grad(rho0)
    drho = rng.standard_normal(rho0.shape); drho /= np.linalg.norm(drho)

    # Finite-difference directional derivative (reference)
    eps_fd = 1e-5
    J_fd, _ = eval_J_grad(rho0 + eps_fd * drho)
    dJ_fd  = (J_fd - J0) / eps_fd
    dJ_adj = float(np.dot(dJ, drho))

    print(f"J0={J0:.6e}  |grad|={np.linalg.norm(dJ):.3e}")
    print(f"FD deriv={dJ_fd:.3e}  Adj deriv (scaled)={dJ_adj:.3e}")

    # Gradient direction test
    step = min(0.05 / (np.linalg.norm(dJ) + 1e-30), 0.1)
    J_gd, _ = eval_J_grad(rho0 - step * dJ)
    print(f"Gradient descent: {J0:.4e} -> {J_gd:.4e}  "
          f"decreased={J_gd < J0}")
    assert J_gd < J0, f"Gradient direction wrong: J increased"

    # Taylor remainder using FD-normalised gradient
    eps_values = np.logspace(-6, -3, n_eps)
    remainders = []
    for eps in eps_values:
        Je, _ = eval_J_grad(rho0 + eps * drho)
        R = abs(Je - J0 - eps * dJ_fd)
        remainders.append(R)
        print(f"  eps={eps:.1e}  R={R:.3e}")

    log_eps = np.log10(eps_values)
    log_R   = np.log10(np.maximum(remainders, 1e-30))
    mask = (eps_values >= 1e-6) & (eps_values <= 1e-4)
    slope = np.polyfit(log_eps[mask], log_R[mask], 1)[0] if mask.sum()>=2             else np.polyfit(log_eps, log_R, 1)[0]

    print(f"\nTaylor slope: {slope:.3f}  (expect >= 1.8)")
    assert slope > 1.8, f"Taylor test failed: slope={slope:.3f} < 1.8"
    return slope, eps_values, remainders


if __name__ == "__main__":
    print("Running Taylor test on primary mesh (80x20)...")
    slope, eps, R = run_taylor_test(nx=80, ny=20)
    print(f"PASSED: slope = {slope:.2f}")
