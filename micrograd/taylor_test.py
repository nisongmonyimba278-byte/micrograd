"""
Taylor remainder test for the reduced functional J(rho).

Verifies that the continuous adjoint gradient is correct:
  R(eps) = |J(rho + eps*drho) - J(rho) - eps * dJ/drho[drho]|

should decay as eps^2 (second-order) if the gradient is exact.

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


def run_taylor_test(nx=20, ny=5, n_eps=7, seed=42,
                    w_f=1e-7, w_c=5e4, alpha_max=1e3):
    """
    Taylor remainder test on the specified mesh.

    Uses the original correct formulation:
      - perturb rho (raw design variable)
      - reapply filter + projection
      - compute dJ/drho[drho] = dot(grad_vec, drho)  (L2 inner product)
      - verify R(eps) = O(eps^2)
    """
    rng = np.random.default_rng(seed)

    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=nx, ny=ny,
        target_expr=lambda x: x[1] / 500e-6,
        w_f=w_f, w_c=w_c, V_star=0.5,
    )
    _ut.alpha_max = alpha_max
    opt.run(max_iter=5, beta_continuation=[1], move=0.2)

    rho0 = opt.rho.x.array.copy()
    helmholtz_filter(opt.rho, opt.rho_filt, opt.V_rho, opt.r_filter)
    heaviside_projection(opt.rho_filt, opt.rho_phys, 1)

    u_h, p_h, c_h = forward_solve(opt.msh, opt.boundary_data,
                                   opt.rho_phys, P_in=1000.0)
    c_h.x.array[:] = np.clip(c_h.x.array, 0.0, 1.0)
    c_h.x.scatter_forward()

    J0, grad = adjoint_and_sensitivity(
        opt.msh, opt.boundary_data, opt.rho_phys,
        u_h, c_h, opt.target_expr,
        w_f=w_f, w_c=w_c,
    )

    drho = rng.standard_normal(rho0.shape)
    drho /= np.linalg.norm(drho)
    # L2 directional derivative: <dJ/drho, drho> = dot(grad_vec, drho)
    dJ_drho = float(np.dot(grad.array, drho))

    print(f"J0={J0:.6e}  |grad|={np.linalg.norm(grad.array):.3e}"
          f"  dJ_drho={dJ_drho:.3e}")

    eps_values = np.logspace(-8, -2, n_eps)
    remainders = []
    for eps in eps_values:
        opt.rho.x.array[:] = rho0 + eps * drho
        opt.rho.x.scatter_forward()
        helmholtz_filter(opt.rho, opt.rho_filt, opt.V_rho, opt.r_filter)
        heaviside_projection(opt.rho_filt, opt.rho_phys, 1)
        u_e, p_e, c_e = forward_solve(opt.msh, opt.boundary_data,
                                       opt.rho_phys, P_in=1000.0)
        c_e.x.array[:] = np.clip(c_e.x.array, 0.0, 1.0)
        c_e.x.scatter_forward()
        Je, _ = adjoint_and_sensitivity(
            opt.msh, opt.boundary_data, opt.rho_phys,
            u_e, c_e, opt.target_expr,
            w_f=w_f, w_c=w_c,
        )
        R = abs(Je - J0 - eps * dJ_drho)
        remainders.append(R)
        print(f"  eps={eps:.1e}  R={R:.3e}")

    log_eps = np.log10(eps_values)
    log_R   = np.log10(np.array(remainders) + 1e-30)
    # Use middle range to avoid round-off at small eps and nonlinearity at large
    mask = (eps_values >= 1e-7) & (eps_values <= 1e-4)
    if mask.sum() >= 2:
        slope = np.polyfit(log_eps[mask], log_R[mask], 1)[0]
    else:
        slope = np.polyfit(log_eps, log_R, 1)[0]

    print(f"\nTaylor slope: {slope:.3f}  (expect >= 1.8)")
    return slope, eps_values, remainders


if __name__ == "__main__":
    print("=== Taylor test on 20x5 (manuscript mesh) ===")
    slope_20, eps, R = run_taylor_test(nx=20, ny=5)
    print(f"20x5 slope = {slope_20:.2f}")

    print("\n=== Taylor test on 80x20 (primary mesh) ===")
    slope_80, eps, R = run_taylor_test(nx=80, ny=20)
    print(f"80x20 slope = {slope_80:.2f}")

    print(f"\nSummary: 20x5={slope_20:.2f}  80x20={slope_80:.2f}")
    assert slope_20 > 1.8, f"20x5 Taylor test failed: slope={slope_20:.3f}"
    assert slope_80 > 1.8, f"80x20 Taylor test failed: slope={slope_80:.3f}"
    print("PASSED")
