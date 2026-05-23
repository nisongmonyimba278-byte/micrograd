import numpy as np, matplotlib.pyplot as plt, os
from micrograd import GradientGeneratorOptimizer

def main():
    os.makedirs('figures', exist_ok=True)
    targets = {
        'Linear': lambda x: x[1]/500e-6,
        'Sigmoid': lambda x: 1/(1+np.exp(-20*(x[1]/500e-6 - 0.5))),
        'Double peak': lambda x: np.sin(np.pi*x[1]/500e-6)**2,
        'Stair-step': lambda x: np.where(x[1]<167e-6, 0.1, np.where(x[1]<333e-6, 0.5, 0.9))
    }
    fig, axes = plt.subplots(4,2, figsize=(10,12))
    for i, (name, func) in enumerate(targets.items()):
        opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=40, ny=10,
                                         target_expr=func, V_star=0.5)
        rho_phys = opt.run(max_iter=40, beta_continuation=[1,2,4,8,16])
        c_h = opt.c_h; x = opt.msh.geometry.x
        outlet_nodes = np.where(np.isclose(x[:,0], opt.Lx))[0]
        y_out = x[outlet_nodes,1]; c_out = c_h.x.array[outlet_nodes]
        idx = np.argsort(y_out); y_out, c_out = y_out[idx], c_out[idx]
        axes[i,0].plot(y_out*1e6, c_out, 'b-', label='Simulated')
        axes[i,0].plot(y_out*1e6, func(np.array([np.zeros_like(y_out), y_out])), 'k--', label='Target')
        axes[i,0].set_title(name); axes[i,0].legend()
        axes[i,1].hist(rho_phys.x.array, bins=50, color='steelblue', edgecolor='k')
        axes[i,1].set_title('Density distribution')
    plt.tight_layout()
    plt.savefig('figures/gallery_profiles.pdf'); plt.close()
    print("Gallery saved to figures/gallery_profiles.pdf")
if __name__ == "__main__":
    main()
