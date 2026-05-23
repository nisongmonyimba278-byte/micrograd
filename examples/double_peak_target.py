from micrograd import GradientGeneratorOptimizer
import matplotlib.pyplot as plt
import numpy as np, os

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=40, ny=10,
                                     target_expr=lambda x: np.sin(np.pi*x[1]/500e-6)**2,
                                     V_star=0.5)
    rho_phys = opt.run(max_iter=40, beta_continuation=[1,2,4,8,16])
    c_h = opt.c_h; x = opt.msh.geometry.x
    outlet_nodes = np.where(np.isclose(x[:,0], opt.Lx))[0]
    y_out = x[outlet_nodes,1]; c_out = c_h.x.array[outlet_nodes]
    idx = np.argsort(y_out); y_out, c_out = y_out[idx], c_out[idx]
    plt.figure()
    plt.plot(y_out*1e6, c_out, 'b-', label='Optimised')
    plt.plot(y_out*1e6, np.sin(np.pi*y_out/500e-6)**2, 'k--', label='Target')
    plt.xlabel('y (µm)'); plt.ylabel('Concentration'); plt.legend()
    plt.title('Double‑peak outlet profile')
    plt.savefig('figures/double_peak_outlet.pdf'); plt.close()
    print("Double‑peak profile saved to figures/double_peak_outlet.pdf")
if __name__ == "__main__":
    main()
