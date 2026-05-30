# adjoint.py — penalty method (homogeneous BCs)
import numpy as np, basix.ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem as _LinearProblem

def _LP(a, L, bcs, petsc_options_prefix, petsc_options):
    try:
        return _LinearProblem(a, L, bcs=bcs,
                              petsc_options_prefix=petsc_options_prefix,
                              petsc_options=petsc_options)
    except TypeError:
        return _LinearProblem(a, L, bcs=bcs, petsc_options=petsc_options)
import ufl
import basix.ufl
from petsc4py import PETSc
from .utilities import alpha, D_eff, D_min, p_simp
from . import utilities as _ut  # read alpha_max dynamically for continuation

def adjoint_and_sensitivity(msh, boundary_data, rho_phys, u_h, c_h, target_expr,
                            mu=1e-3, D_fluid=1e-9, w_f=1e-7, w_c=1.0):
    P2 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 2,
                            shape=(msh.geometry.dim,))
    P1 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 1)
    W  = fem.functionspace(msh, basix.ufl.mixed_element([P2, P1]))
    Vc = fem.functionspace(msh, ("Lagrange", 1))
    Vv = fem.functionspace(msh, ("Lagrange", 2, (msh.geometry.dim,)))
    V_rho = rho_phys.function_space

    i1 = boundary_data["inlet1"]; i2 = boundary_data["inlet2"]
    out = boundary_data["outlet"]; walls = boundary_data["walls"]
    ft  = boundary_data["facet_tag"]; fd = msh.topology.dim - 1
    ds_out = ufl.Measure("ds", domain=msh, subdomain_data=ft, subdomain_id=3)

    # ---- Concentration adjoint ----
    lam, phi = ufl.TrialFunction(Vc), ufl.TestFunction(Vc)
    D = D_eff(rho_phys, D_fluid); uv = u_h
    hc = ufl.CellDiameter(msh); um = ufl.sqrt(ufl.dot(uv, uv) + 1e-20)
    Pe = um * hc / (2.0 * D); tau = hc / (2.0 * um) * (1.0 / ufl.tanh(Pe) - 1.0 / Pe)
    a_lam = (-ufl.dot(uv, ufl.grad(lam)) * phi * ufl.dx
             + D * ufl.inner(ufl.grad(lam), ufl.grad(phi)) * ufl.dx
             + tau * ufl.dot(uv, ufl.grad(lam)) * ufl.dot(uv, ufl.grad(phi)) * ufl.dx)
    L_lam = fem.Constant(msh, 0.0) * phi * ufl.dx
    delta = fem.Function(Vc); delta.interpolate(target_expr)
    delta.x.array[:] -= c_h.x.array[:]; delta.x.scatter_forward()
    bc_lo = fem.dirichletbc(delta, fem.locate_dofs_topological(Vc, fd, out))
    bc_l1 = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(Vc, fd, i1), Vc)
    bc_l2 = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(Vc, fd, i2), Vc)
    lam_h = _LP(a_lam, L_lam, bcs=[bc_l1, bc_l2, bc_lo], petsc_options_prefix="lp1_", petsc_options={"ksp_type":"preonly","pc_type":"lu"}).solve()

    # ---- Flow adjoint (homogeneous Dirichlet on walls via penalty) ----
    (v_a, q_a) = ufl.TrialFunctions(W)
    (w_s, s_t) = ufl.TestFunctions(W)

    a_adj = (mu * ufl.inner(ufl.grad(v_a), ufl.grad(w_s)) * ufl.dx
             + alpha(rho_phys) * ufl.inner(v_a, w_s) * ufl.dx
             - q_a * ufl.div(w_s) * ufl.dx
             - s_t * ufl.div(v_a) * ufl.dx)
    # Dirichlet no-slip on walls
    W0, _ = W.sub(0).collapse()
    zero_fn = fem.Function(W0)
    zero_fn.x.array[:] = 0.0
    dofs_walls = fem.locate_dofs_topological((W.sub(0), W0), fd, walls)
    bc_walls_adj = fem.dirichletbc(zero_fn, dofs_walls, W.sub(0))
    # Pin adjoint pressure at outlet to remove nullspace
    W1, _ = W.sub(1).collapse()
    dofs_p = fem.locate_dofs_topological((W.sub(1), W1), fd, out)
    zero_p = fem.Function(W1); zero_p.x.array[:] = 0.0
    bc_p_adj = fem.dirichletbc(zero_p, dofs_p, W.sub(1))

    rhs_expr = lam_h * ufl.grad(c_h)
    rhs_func = fem.Function(Vv)
    rhs_func.interpolate(fem.Expression(rhs_expr, Vv.element.interpolation_points))
    L_adj = - ufl.inner(rhs_func, w_s) * ufl.dx

    w_adj = _LP(a_adj, L_adj, bcs=[bc_walls_adj, bc_p_adj], petsc_options_prefix="lp2_", petsc_options={"ksp_type":"preonly","pc_type":"lu"}).solve()
    vh = w_adj.sub(0).collapse(); qh = w_adj.sub(1).collapse()

    # ---- Objective ----
    Jf = fem.assemble_scalar(fem.form(0.5*mu*ufl.inner(ufl.grad(u_h), ufl.grad(u_h))*ufl.dx
                                      + 0.5*alpha(rho_phys)*ufl.inner(u_h, u_h)*ufl.dx))
    Jc = fem.assemble_scalar(fem.form(0.5*ufl.inner(delta, delta) * ds_out))
    J = float(w_f*Jf + w_c*Jc)

    drho_dalpha = -(_ut.alpha_max - _ut.alpha_min)*2.0/(1.0+rho_phys)**2
    drho_dD = p_simp*(D_fluid-D_min)*rho_phys**(p_simp-1)
    test_rho = ufl.TestFunction(V_rho)
    sens_form = (drho_dalpha * ufl.inner(u_h, vh) * test_rho
                 + drho_dD * ufl.inner(ufl.grad(c_h), ufl.grad(lam_h)) * test_rho) * ufl.dx
    sens_vec = fem.petsc.assemble_vector(fem.form(sens_form))
    sens_vec.ghostUpdate()
    return J, sens_vec
