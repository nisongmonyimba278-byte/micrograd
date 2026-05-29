# micrograd/optimizer.py
"""Design update routines: OC and Svanberg MMA (self-contained)."""
import numpy as np
from dolfinx import fem
import ufl
from .compatibility import check_mma_available


# ─── OC update ────────────────────────────────────────────────────────────────
def oc_update(rho_vec, sens_vec, V_rho, vol_frac_target, move=0.2,
              eta=0.5, rho_min=0.001, rho_max=1.0):
    v_test = ufl.TestFunction(V_rho)
    M = fem.petsc.assemble_vector(fem.form(v_test * ufl.dx))
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
        rho_new = np.maximum(rho_vec - move, np.minimum(rho_vec + move, rho_new))
        vol = np.dot(m_i, rho_new)
        if vol > target_vol: l1 = lmid
        else:                l2 = lmid
        if l2 - l1 < 1e-8:  break
    return rho_new


# ─── gcma MMA (kept for compatibility) ───────────────────────────────────────
class MMAUpdater:
    def __init__(self, n_vars, m=1):
        if not check_mma_available():
            raise ImportError("gcma not available. Use method='nlopt_mma'.")
        from gcma import MMASolver
        self.solver = MMASolver(n_vars, m)
        self.iter = 0

    def update(self, x, obj, grad_obj, g, dg, xmin, xmax):
        g = np.atleast_1d(g); dg = np.atleast_2d(dg)
        self.solver.MMASub(x, obj, grad_obj, g, dg, xmin, xmax)
        self.iter += 1
        return self.solver.x.copy()


def mma_update(rho_vec, sens_vec, V_rho, vol_frac_target, mma_updater,
               move=0.2, rho_min=0.001, rho_max=1.0):
    v_test = ufl.TestFunction(V_rho)
    M = fem.petsc.assemble_vector(fem.form(v_test * ufl.dx))
    M.ghostUpdate()
    m_i = M.array
    current_vol = np.dot(m_i, rho_vec)
    total_mass  = np.sum(m_i)
    g_vol  = current_vol - vol_frac_target * total_mass
    dg_vol = m_i.copy()
    grad_obj = sens_vec.array.copy()
    xmin = np.maximum(np.full_like(rho_vec, rho_min), rho_vec - move)
    xmax = np.minimum(np.full_like(rho_vec, rho_max), rho_vec + move)
    return mma_updater.update(rho_vec, 0.0, grad_obj, [g_vol], [dg_vol], xmin, xmax)


# ─── Svanberg MMA — self-contained, no external package ──────────────────────
class _MMAState:
    def __init__(self, n):
        self.iter  = 0
        self.x_old1 = None
        self.x_old2 = None
        self.low    = None
        self.upp    = None
        self.n      = n

_mma_state = None

def reset_mma_state():
    global _mma_state
    _mma_state = None

def nlopt_mma_update(rho_vec, sens_vec, V_rho, vol_frac_target,
                     move=0.2, rho_min=0.001, rho_max=1.0):
    """
    One outer MMA step (Svanberg 1987/2002).
    Key fix: sensitivity normalised to L-inf=1 so objective and volume
    constraint gradients are on the same scale in the dual problem.
    """
    global _mma_state
    n = len(rho_vec)
    if _mma_state is None or _mma_state.n != n:
        _mma_state = _MMAState(n)
    st = _mma_state

    x    = rho_vec.copy()
    xmin = np.full(n, rho_min)
    xmax = np.full(n, rho_max)

    # Volume constraint
    v_test = ufl.TestFunction(V_rho)
    M_vec  = fem.petsc.assemble_vector(fem.form(v_test * ufl.dx))
    M_vec.ghostUpdate()
    m_i   = M_vec.array.copy()
    M_tot = m_i.sum()
    dg    = m_i / M_tot
    g_val = float(np.dot(m_i, x) / M_tot) - vol_frac_target

    # Normalise objective gradient to [-1,1]
    df0_raw = sens_vec.array.copy()
    scale   = np.abs(df0_raw).max()
    df0     = df0_raw / (scale if scale > 1e-30 else 1.0)

    # Asymptotes
    if st.iter < 2:
        low = x - 0.5 * (xmax - xmin)
        upp = x + 0.5 * (xmax - xmin)
    else:
        osc   = (x - st.x_old1) * (st.x_old1 - st.x_old2)
        gamma = np.where(osc < 0, 0.65, 1.08)
        low   = x - gamma * (st.x_old1 - st.low)
        upp   = x + gamma * (st.upp   - st.x_old1)

    low = np.minimum(low, x - 0.01*(xmax - xmin))
    upp = np.maximum(upp, x + 0.01*(xmax - xmin))
    low = np.maximum(low, xmin - 10*(xmax - xmin))
    upp = np.minimum(upp, xmax + 10*(xmax - xmin))

    # Move limits
    alp = np.maximum(xmin, np.maximum(x - move, low + 0.1*(x - low)))
    bet = np.minimum(xmax, np.minimum(x + move, upp - 0.1*(upp - x)))
    alp = np.minimum(alp, bet - 1e-6)

    # MMA approximation coefficients
    ux  = upp - x;  xl  = x - low
    ux2 = ux**2;    xl2 = xl**2
    eps = 1e-6 * (ux2 + xl2).mean()

    p0 = ux2 * np.maximum( df0, 0) + eps
    q0 = xl2 * np.maximum(-df0, 0) + eps
    pg = ux2 * np.maximum( dg,  0) + eps
    qg = xl2 * np.maximum(-dg,  0) + eps

    def x_of_mu(mu):
        ratio = np.sqrt((p0 + mu*pg) / (q0 + mu*qg + 1e-300))
        return np.clip((low*ratio + upp) / (1.0 + ratio), alp, bet)

    # Auto-bracket mu_hi
    mu_lo, mu_hi = 0.0, 1.0
    for _ in range(60):
        if float(np.dot(m_i, x_of_mu(mu_hi)) / M_tot) - vol_frac_target < 0:
            break
        mu_hi *= 10.0

    # Bisect
    for _ in range(100):
        mu_mid = 0.5*(mu_lo + mu_hi)
        gm = float(np.dot(m_i, x_of_mu(mu_mid)) / M_tot) - vol_frac_target
        if gm > 0: mu_lo = mu_mid
        else:      mu_hi = mu_mid
        if mu_hi - mu_lo < 1e-12*(1.0 + mu_hi): break

    x_new = np.clip(x_of_mu(0.5*(mu_lo + mu_hi)), alp, bet)

    st.x_old2 = st.x_old1.copy() if st.x_old1 is not None else x.copy()
    st.x_old1 = x.copy()
    st.low    = low.copy()
    st.upp    = upp.copy()
    st.iter  += 1
    return x_new
