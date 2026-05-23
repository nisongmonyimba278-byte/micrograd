import basix.ufl
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
import ufl
from petsc4py import PETSc
from .utilities import alpha, D_eff

def forward_solve(msh, boundary_data, rho_phys, mu=1e-3, D_fluid=1e-9,
                  P_in=1000.0, solver_type="direct"):
    i1 = boundary_data["inlet1"]; i2 = boundary_data["inlet2"]
    out = boundary_data["outlet"]; walls = boundary_data["walls"]
    fd = msh.topology.dim - 1
    P2 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 2, shape=(msh.geometry.dim,))
    P1 = basix.ufl.element("Lagrange", msh.topology.cell_name(), 1)
    W  = fem.functionspace(msh, basix.ufl.mixed_element([P2, P1]))
    Vc = fem.functionspace(msh, ("Lagrange", 1))
    (u, p) = ufl.TrialFunctions(W); (v, q) = ufl.TestFunctions(W)
    a = (mu * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
         + alpha(rho_phys) * ufl.inner(u, v) * ufl.dx
         - p * ufl.div(v) * ufl.dx
         - q * ufl.div(u) * ufl.dx)
    L = (ufl.inner(fem.Constant(msh, PETSc.ScalarType((0., 0.))), v) * ufl.dx
         + fem.Constant(msh, PETSc.ScalarType(0.)) * q * ufl.dx)
    W0, W1 = W.sub(0), W.sub(1)
    Vu, _ = W0.collapse(); Vp, _ = W1.collapse()
    u_zero = fem.Function(Vu); u_zero.x.array[:] = 0.0; u_zero.x.scatter_forward()
    bc_walls = fem.dirichletbc(u_zero, fem.locate_dofs_topological((W0, Vu), fd, walls), W0)
    p_in = fem.Function(Vp); p_in.x.array[:] = P_in; p_in.x.scatter_forward()
    p_out = fem.Function(Vp); p_out.x.array[:] = 0.0; p_out.x.scatter_forward()
    bc_i1 = fem.dirichletbc(p_in,  fem.locate_dofs_topological((W1, Vp), fd, i1),  W1)
    bc_i2 = fem.dirichletbc(p_in,  fem.locate_dofs_topological((W1, Vp), fd, i2),  W1)
    bc_out = fem.dirichletbc(p_out, fem.locate_dofs_topological((W1, Vp), fd, out), W1)
    wh = LinearProblem(a, L, bcs=[bc_walls, bc_i1, bc_i2, bc_out],
                       petsc_options={"ksp_type": "preonly", "pc_type": "lu"}, petsc_options_prefix="lp1_").solve()
    uh = wh.sub(0).collapse(); ph = wh.sub(1).collapse()
    c, d = ufl.TrialFunction(Vc), ufl.TestFunction(Vc)
    D = D_eff(rho_phys, D_fluid); hc = ufl.CellDiameter(msh)
    um = ufl.sqrt(ufl.dot(uh, uh) + 1e-20); Pe = um * hc / (2.0 * D)
    tau = hc / (2.0 * um) * (1.0 / ufl.tanh(Pe) - 1.0 / Pe)
    a_c = (ufl.dot(uh, ufl.grad(c)) * d * ufl.dx
           + D * ufl.inner(ufl.grad(c), ufl.grad(d)) * ufl.dx
           + tau * ufl.dot(uh, ufl.grad(c)) * ufl.dot(uh, ufl.grad(d)) * ufl.dx)
    Lc = fem.Constant(msh, PETSc.ScalarType(0.0)) * d * ufl.dx
    bc_c1 = fem.dirichletbc(PETSc.ScalarType(1.0), fem.locate_dofs_topological(Vc, fd, i1), Vc)
    bc_c2 = fem.dirichletbc(PETSc.ScalarType(0.0), fem.locate_dofs_topological(Vc, fd, i2), Vc)
    ch = LinearProblem(a_c, Lc, bcs=[bc_c1, bc_c2],
                       petsc_options={"ksp_type": "preonly", "pc_type": "lu"}, petsc_options_prefix="lp2_").solve()
    return uh, ph, ch