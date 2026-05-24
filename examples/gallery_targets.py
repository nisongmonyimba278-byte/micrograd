from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, os
from dolfinx import fem

def run_target(name, target_fn):
    opt = GradientGeneratorOptimizer(
        Lx=2000e-6, Ly=500e-6, nx=20, ny=5,
        target_expr=target_fn, w_f=1e-7, w_c=5e4, V_star=0.5)
    opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
    c_h = opt.c_h
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, opt.boundary_data["outlet"])
    y_out = opt.msh.geometry.x[dofs, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out)
    return y_out[idx], c_out[idx]

def main():
    os.makedirs('figures', exist_ok=True)
    Ly = 500e-6
    targets = {
        'Linear':      lambda x: x[1]/Ly,
        'Parabolic':   lambda x: (x[1]/Ly)**2,
        'Double-peak': lambda x: 4*(x[1]/Ly)*(1-x[1]/Ly),
        'Step':        lambda x: np.where(x[1] < Ly/2, 0.2, 0.8),
    }
    fig, axes = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
    for ax, (name, fn) in zip(axes, targets.items()):
        y_s, c_s = run_target(name, fn)
        y_t = np.linspace(0, Ly, 100)
        ax.plot(c_s, y_s*1e6, 'b-', label='TopOpt')
        ax.plot(fn(np.array([np.zeros(100), y_t])), y_t*1e6, 'r--', label='Target')
        ax.set_title(name); ax.set_xlabel('c')
    axes[0].set_ylabel('y (µm)')
    fig.savefig('figures/gallery_profiles.pdf', bbox_inches='tight'); plt.close()
    print("Gallery saved to figures/gallery_profiles.pdf")

if __name__ == '__main__': main()
