from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, os
from dolfinx import fem
import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    target = lambda x: 4*(x[1]/500e-6)*(1 - x[1]/500e-6)
    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=20, ny=5,
        target_expr=target, w_f=1e-7, w_c=5e4, V_star=0.5)
    opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
    c_h = opt.c_h
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, opt.boundary_data["outlet"])
    y_out = opt.msh.geometry.x[dofs, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_s, c_s = y_out[idx], c_out[idx]
    Ly = 500e-6
    fig, ax = plt.subplots()
    ax.plot(y_s*1e6, c_s, 'b-', label='TopOpt')
    ax.plot(y_s*1e6, 4*(y_s/Ly)*(1-y_s/Ly), 'r--', label='Target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/double_peak_outlet.pdf', bbox_inches='tight'); plt.close()
    rmse = float(np.sqrt(np.mean((np.clip(c_s,0,1) - 4*(y_s/Ly)*(1-y_s/Ly))**2)))
    print(f"Double-peak RMSE = {rmse:.4e}")
    print("Double‑peak profile saved to figures/double_peak_outlet.pdf")

if __name__ == '__main__': main()
