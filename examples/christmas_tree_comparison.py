from micrograd import GradientGeneratorOptimizer
from micrograd.christmas_tree import create_christmas_tree_density, simulate_christmas_tree
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, os
from dolfinx import fem
import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    Ly = 500e-6
    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=Ly, nx=20, ny=5,
        target_expr=lambda x: x[1]/Ly, w_f=1e-7, w_c=5e4, V_star=0.5)
    rho_opt = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)

    c_h = opt.c_h
    ft  = opt.boundary_data["facet_tag"]
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, opt.boundary_data["outlet"])
    y_out = opt.msh.geometry.x[dofs, 1]
    idx   = np.argsort(y_out); y_s = y_out[idx]
    c_opt = c_h.x.array[dofs][idx]

    rho_tree = create_christmas_tree_density(opt.msh, Lx=opt.Lx, Ly=opt.Ly)
    tree_res = simulate_christmas_tree(opt.msh, opt.boundary_data, rho_tree, opt.target_expr)
    c_tree   = tree_res["concentration"].x.array[dofs][idx]

    fig, ax = plt.subplots()
    ax.plot(y_s*1e6, c_opt,  'b-',  label='TopOpt')
    ax.plot(y_s*1e6, c_tree, 'g--', label='Christmas tree')
    ax.plot(y_s*1e6, y_s/Ly, 'r:',  label='Target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/comparison.pdf', bbox_inches='tight'); plt.close()
    print("Comparison saved to figures/comparison.pdf")

if __name__ == '__main__': main()
