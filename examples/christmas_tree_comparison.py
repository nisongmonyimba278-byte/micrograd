from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os, csv
from dolfinx import fem

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: x[1]/500e-6,
                                     w_f=1e-7, w_c=5e4, V_star=0.5)
    # rho initialised internally by optimizer
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.2)
    c_h = opt.c_h; x = opt.msh.geometry.x
    outlet_facets = opt.boundary_data["outlet"]
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, outlet_facets)
    y_out = x[dofs,1]; c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_s, c_s = y_out[idx], c_out[idx]
    fig,ax=plt.subplots(); ax.plot(y_s*1e6,c_s,'b-',label='TopOpt')
    ax.plot(y_s*1e6, y_s/500e-6, 'r--', label='target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/comparison.pdf')
    print("Comparison saved to figures/comparison.pdf")
if __name__=='__main__': main()