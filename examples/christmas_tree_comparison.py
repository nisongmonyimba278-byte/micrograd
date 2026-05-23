import numpy as np, matplotlib.pyplot as plt, os
from micrograd.christmas_tree import create_christmas_tree_density, simulate_christmas_tree
from micrograd import GradientGeneratorOptimizer

def main():
    os.makedirs('figures', exist_ok=True)
    # Topology-optimised
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=40, ny=10,
                                     target_expr=lambda x: x[1]/500e-6, V_star=0.5)
    rho_opt = opt.run(max_iter=40, beta_continuation=[1,2,4,8,16])
    c_opt = opt.c_h; x = opt.msh.geometry.x
    nodes_opt = np.where(np.isclose(x[:,0], opt.Lx))[0]
    y_opt = x[nodes_opt,1]; c_opt_vals = c_opt.x.array[nodes_opt]
    idx = np.argsort(y_opt); y_opt, c_opt_vals = y_opt[idx], c_opt_vals[idx]

    # Christmas tree
    rho_tree = create_christmas_tree_density(opt.msh, Lx=opt.Lx, Ly=opt.Ly)
    tree_res = simulate_christmas_tree(opt.msh, opt.boundary_data, rho_tree, lambda x: x[1]/500e-6)
    c_tree = tree_res["concentration"]
    nodes_tree = np.where(np.isclose(x[:,0], opt.Lx))[0]
    y_tree = x[nodes_tree,1]; c_tree_vals = c_tree.x.array[nodes_tree]
    idx = np.argsort(y_tree); y_tree, c_tree_vals = y_tree[idx], c_tree_vals[idx]

    plt.figure()
    plt.plot(y_opt*1e6, c_opt_vals, 'b-', label='TopOpt')
    plt.plot(y_tree*1e6, c_tree_vals, 'r-', label='Christmas tree')
    plt.plot([0,500], [0,1], 'k--', label='Target')
    plt.xlabel('y (µm)'); plt.ylabel('Concentration'); plt.legend()
    plt.title('Comparison: TopOpt vs. Christmas tree')
    plt.savefig('figures/comparison.pdf'); plt.close()
    print("Comparison saved to figures/comparison.pdf")
if __name__ == "__main__":
    main()
