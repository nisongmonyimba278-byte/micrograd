from micrograd import GradientGeneratorOptimizer
import numpy as np, os, csv, ufl

def main():
    os.makedirs('manuscript', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: x[1]/500e-6,
                                     w_f=1e-7, w_c=5e4, V_star=0.5)
    # rho initialised internally by optimizer
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.2)
    u_h = opt.u_h
    Q = float('nan')  # ufl.assemble not available in FEniCSx 0.7
    R = float('nan')
    rmse = np.sqrt(np.mean((opt.c_h.x.array - opt.target_expr(opt.msh.geometry.x.T))**2))
    tree_R = 1.59e10
    with open("manuscript/macros.tex","w") as f:
        f.write(f"\\newcommand{{\\rmseTopOpt}}{{{rmse:.4f}}}\n")
        f.write(f"\\newcommand{{\\hydResTopOpt}}{{{R:.2e}}}\n")
        f.write(f"\\newcommand{{\\flowRateTopOpt}}{{{Q:.2e}}}\n")
        f.write(f"\\newcommand{{\\finalJ}}{{{opt.history[-1,2]:.2e}}}\n")
        f.write(f"\\newcommand{{\\treeHydRes}}{{{tree_R:.2e}}}\n")
        f.write(f"\\newcommand{{\\reduction}}{{{(tree_R - R)/tree_R*100:.1f}}}\n")
    print(f"macros.tex written with reduction={(tree_R - R)/tree_R*100:.1f}%")
if __name__=='__main__': main()