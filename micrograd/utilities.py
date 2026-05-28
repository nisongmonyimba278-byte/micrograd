import ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
import numpy as np
from petsc4py import PETSc

alpha_min=1e-4; alpha_max=1e3; D_min=1e-15; p_simp=3.0  # alpha_max ramped in optimizer
def alpha(r): return alpha_min + (alpha_max-alpha_min)*(1.0-r)/(1.0+r)
def D_eff(r, Df=1e-9): return D_min + (Df-D_min)*r**p_simp

def helmholtz_filter(rin, rout, V, rf):
    u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
    a = rf**2*ufl.inner(ufl.grad(u),ufl.grad(v))*ufl.dx + u*v*ufl.dx
    L = rin * v * ufl.dx
    res = LinearProblem(a, L, bcs=[], petsc_options={"ksp_type":"cg","pc_type":"jacobi"}).solve()
    rout.x.array[:] = res.x.array[:]; rout.x.scatter_forward()

def heaviside_projection(r, rout, b, e=0.5):
    expr = (ufl.tanh(b*e)+ufl.tanh(b*(r-e)))/(ufl.tanh(b*e)+ufl.tanh(b*(1.0-e)))
    rout.interpolate(fem.Expression(expr, rout.function_space.element.interpolation_points))
    rout.x.scatter_forward()