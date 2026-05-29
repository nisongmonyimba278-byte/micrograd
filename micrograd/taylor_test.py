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
from dolfinx import fem


def run_taylor_test(nx=20, ny=5, n_eps=7, seed=42):
    rng = np.random.default_rng(seed)

    # Build optimizer and run 5 iterations to get a non-trivial design point
    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=nx, ny=ny,
        target_expr=lambda x: x[1] / 500e-6,
        w_f=1e-7, w_c=5e4, V_star=0.5,
    )
    opt.run(max_iter=5, beta_continuation=[1], move=0.2)

    # Evaluate J and dJ/drho at current design
    from micrograd.adjoint import adjoint_and_sensitivity
    from micrograd.utilities import helmholtz_filter, heaviside_projection

    rho0 = opt.rho.x.array.copy()
    helmholtz_filter(opt.rho, opt.rho_filt, opt.V_rho, opt.r_filter)
    heaviside_projection(opt.rho_filt, opt.rho_phys, beta=1)

    from micrograd.solver import forward_solve
    u_h, p_h, c_h = forward_solve(opt.msh, opt.boundary_data,
                                   opt.rho_phys, P_in=1000.0)
    import numpy as np
    c_h.x.array[:] = np.clip(c_h.x.array, 0.0, 1.0)
    c_h.x.scatter_forward()

    J0, grad = adjoint_and_sensitivity(
        opt.msh, opt.boundary_data, opt.rho_phys,
        u_h, c_h, opt.target_expr,
        w_f=opt.w_f, w_c=opt.w_c,
    )

    # Random perturbation direction
    drho = rng.standard_normal(rho0.shape)
    drho /= np.linalg.norm(drho)
    dJ_drho = float(np.dot(grad, drho))

    # Taylor remainder test
    eps_values = np.logspace(-8, -2, n_eps)
    remainders = []
    for eps in eps_values:
        opt.rho.x.array[:] = rho0 + eps * drho
        opt.rho.x.scatter_forward()
        helmholtz_filter(opt.rho, opt.rho_filt, opt.V_rho, opt.r_filter)
        heaviside_projection(opt.rho_filt, opt.rho_phys, beta=1)
        u_e, p_e, c_e = forward_solve(opt.msh, opt.boundary_data,
                                       opt.rho_phys, P_in=1000.0)
        c_e.x.array[:] = np.clip(c_e.x.array, 0.0, 1.0)
        c_e.x.scatter_forward()
        Je, _ = adjoint_and_sensitivity(
            opt.msh, opt.boundary_data, opt.rho_phys,
            u_e, c_e, opt.target_expr,
            w_f=opt.w_f, w_c=opt.w_c,
        )
        R = abs(Je - J0 - eps * dJ_drho)
        remainders.append(R)
        print(f"  eps={eps:.1e}  R={R:.3e}")

    # Compute slope in log-log space
    log_eps = np.log10(eps_values)
    log_R   = np.log10(np.array(remainders) + 1e-30)
    # Use middle range (avoid round-off at small eps)
    mask = (eps_values >= 1e-7) & (eps_values <= 1e-4)
    if mask.sum() >= 2:
        slope = np.polyfit(log_eps[mask], log_R[mask], 1)[0]
    else:
        slope = np.polyfit(log_eps, log_R, 1)[0]

    print(f"\nTaylor test slope: {slope:.3f}  (expect ≈ 2.0)")
    assert slope > 1.8, f"Taylor test failed: slope={slope:.3f} < 1.8"
    return slope, eps_values, remainders


if __name__ == "__main__":
    slope, eps, R = run_taylor_test()
    print(f"PASSED: slope = {slope:.2f}")
