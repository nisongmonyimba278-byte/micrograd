import ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem as _LinearProblem

def _LP(a, L, bcs, petsc_options_prefix, petsc_options):
    """Version-safe LinearProblem constructor."""
    try:
        return _LinearProblem(a, L, bcs=bcs,
                              petsc_options_prefix=petsc_options_prefix,
                              petsc_options=petsc_options)
    except TypeError:
        return _LinearProblem(a, L, bcs=bcs, petsc_options=petsc_options)
import numpy as np
from petsc4py import PETSc

alpha_min=1e-4; alpha_max=1e3; D_min=1e-15; p_simp=3.0  # alpha_max ramped in optimizer
def alpha(r):
    # floor prevents RMSE=inf when binary_validation sets alpha_min=0
    _raw = alpha_min + (alpha_max - alpha_min) * (1.0 - r) / (1.0 + r)
    return ufl.max_value(_raw, 1e-4)
def D_eff(r, Df=1e-9): return D_min + (Df-D_min)*r**p_simp

def helmholtz_filter(rin, rout, V, rf):
    u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
    a = rf**2*ufl.inner(ufl.grad(u),ufl.grad(v))*ufl.dx + u*v*ufl.dx
    L = rin * v * ufl.dx
    res = _LP(a, L, bcs=[], petsc_options_prefix="lp1_", petsc_options={"ksp_type":"cg","pc_type":"jacobi"}).solve()
    rout.x.array[:] = res.x.array[:]; rout.x.scatter_forward()

def heaviside_projection(r, rout, b, e=0.5):
    expr = (ufl.tanh(b*e)+ufl.tanh(b*(r-e)))/(ufl.tanh(b*e)+ufl.tanh(b*(1.0-e)))
    rout.interpolate(fem.Expression(expr, rout.function_space.element.interpolation_points))
    rout.x.scatter_forward()
def smooth_penalty(c_h, gamma=1e6, delta=1e-6):
    """
    Smooth differentiable penalty for c in [0,1].
    Replaces hard clamping: phi_delta(c) is C-infty and vanishes for c in [0,1].
    
    phi_delta(c) = 0.5*(sqrt(c^2+delta^2)-c)^2 + 0.5*(sqrt((c-1)^2+delta^2)+(c-1))^2
    
    Returns scalar penalty value.
    """
    import numpy as np
    c = c_h.x.array
    phi = (0.5*(np.sqrt(c**2 + delta**2) - c)**2 +
           0.5*(np.sqrt((c-1)**2 + delta**2) + (c-1))**2)
    return float(gamma * phi.sum())

