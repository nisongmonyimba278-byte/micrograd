import numpy as np, matplotlib.pyplot as plt, os
from micrograd import GradientGeneratorOptimizer

def main():
    os.makedirs('figures', exist_ok=True)
    sizes = [(20,5), (30,7), (40,10)]
    rmses = []
    for nx, ny in sizes:
        opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=nx, ny=ny,
                                         target_expr=lambda x: x[1]/500e-6, V_star=0.5)
        rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16,32,64], move=0.05)
        c_h = opt.c_h; x = opt.msh.geometry.x
        outlet_nodes = np.where(np.isclose(x[:,0], opt.Lx))[0]
        y_out = x[outlet_nodes,1]; c_out = c_h.x.array[outlet_nodes]
        idx = np.argsort(y_out); y_out, c_out = y_out[idx], c_out[idx]
        target = y_out / 500e-6
        rmse = np.sqrt(np.mean((c_out - target)**2))
        rmses.append(rmse)
    plt.figure()
    plt.plot([s[0]*s[1] for s in sizes], rmses, 'o-')
    plt.xlabel('Number of elements (nx*ny)'); plt.ylabel('Outlet RMSE')
    plt.title('Mesh convergence')
    plt.savefig('figures/convergence.pdf'); plt.close()
    print("Convergence plot saved to figures/convergence.pdf")
if __name__ == "__main__":
    main()
