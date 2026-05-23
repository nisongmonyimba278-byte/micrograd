# micrograd/optimizer.py
"""Design update routines: Optimality Criteria (OC) and MMA (via gcma)."""
import numpy as np
from dolfinx import fem
import ufl
from .compatibility import check_mma_available


# ─── OC update ─────────────────────────────────────────────────
def oc_update(rho_vec, sens_vec, V_rho, vol_frac_target, move=0.2,
              eta=0.5, rho_min=0.001, rho_max=1.0):
    """
    Standard Optimality Criteria (OC) update for topology optimisation
    with a single volume constraint.

    Args:
        rho_vec: current density array.
        sens_vec: PETSc vector of dJ/dρ.
        V_rho: function space of density.
        vol_frac_target: target volume fraction (0–1).
        move: move limit.
        eta: exponent for OC formula.
        rho_min, rho_max: bounds on density.

    Returns:
        new density array.
    """
    v_test = ufl.TestFunction(V_rho)
    mass_form = fem.form(v_test * ufl.dx)
    M = fem.petsc.assemble_vector(mass_form)
    M.ghostUpdate()
    m_i = M.array

    sens_array = sens_vec.array.copy()
    target_vol = vol_frac_target * np.sum(m_i)

    l1, l2 = 0.0, 1e10
    for _ in range(200):
        lmid = 0.5 * (l1 + l2)
        B = -sens_array / (lmid * m_i + 1e-20)
        rho_new = np.minimum(rho_max, np.maximum(rho_min,
                                                  rho_vec * np.maximum(B, 0)**eta))
        # Move limit
        rho_new = np.maximum(rho_vec - move, np.minimum(rho_vec + move, rho_new))
        vol = np.dot(m_i, rho_new)
        if vol > target_vol:
            l1 = lmid
        else:
            l2 = lmid
        if l2 - l1 < 1e-8:
            break
    return rho_new


# ─── MMA updater ───────────────────────────────────────────────
class MMAUpdater:
    """
    Persistent MMA optimizer that stores the state across iterations.
    Requires the `gcma` package.
    """
    def __init__(self, n_vars, m=1):
        if not check_mma_available():
            raise ImportError(
                "MMA not available. Install 'gcma' or 'nlopt'. "
                "Alternatively, use method='oc'."
            )
        from gcma import MMASolver
        self.solver = MMASolver(n_vars, m)
        self.iter = 0

    def update(self, x, obj, grad_obj, g, dg, xmin, xmax):
        """
        Update design using MMA subproblem.
        Args:
            x: current design (numpy array).
            obj: objective value (scalar, not used by gcma).
            grad_obj: gradient of objective (numpy array).
            g: constraint values (list/array of length m).
            dg: list/array of gradient vectors for each constraint (each same size as x).
            xmin, xmax: bounds.
        Returns:
            new design vector.
        """
        g = np.atleast_1d(g)
        dg = np.atleast_2d(dg)
        self.solver.MMASub(x, obj, grad_obj, g, dg, xmin, xmax)
        x_new = self.solver.x.copy()
        self.iter += 1
        return x_new


def mma_update(rho_vec, sens_vec, V_rho, vol_frac_target, mma_updater,
               move=0.2, rho_min=0.001, rho_max=1.0):
    """
    MMA update using a persistent MMAUpdater.
    The volume constraint and move limits are passed directly to MMA.
    """
    v_test = ufl.TestFunction(V_rho)
    mass_form = fem.form(v_test * ufl.dx)
    M = fem.petsc.assemble_vector(mass_form)
    M.ghostUpdate()
    m_i = M.array

    current_vol = np.dot(m_i, rho_vec)
    total_mass = np.sum(m_i)
    g_vol = current_vol - vol_frac_target * total_mass  # g ≤ 0 means satisfied
    dg_vol = m_i.copy()

    grad_obj = sens_vec.array.copy()
    xmin = np.maximum(np.full_like(rho_vec, rho_min), rho_vec - move)
    xmax = np.minimum(np.full_like(rho_vec, rho_max), rho_vec + move)

    rho_new = mma_updater.update(rho_vec, 0.0, grad_obj,
                                 [g_vol], [dg_vol], xmin, xmax)
    return rho_new