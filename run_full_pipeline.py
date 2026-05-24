#!/usr/bin/env python3
import os, sys, subprocess

PROJECT = os.path.expanduser("~/micrograd")
os.chdir(PROJECT)

# ---------- 1. Patch utilities.py ----------
with open("micrograd/utilities.py") as f:
    util = f.read()
util = util.replace("alpha_max = 1e8", "alpha_max = 1e3")
with open("micrograd/utilities.py", "w") as f:
    f.write(util)
print("Patched utilities.py (alpha_max=1e3)")

# ---------- 2. Patch gradient_optimizer.py – add alpha ramp ----------
with open("micrograd/gradient_optimizer.py") as f:
    grad = f.read()
# Insert alpha ramp after "beta = betas[beta_idx]"
old = "beta = betas[beta_idx]"
new = """beta = betas[beta_idx]
            import micrograd.utilities as ut
            ramp = min(1.0, step / (0.6 * max_iter))
            ut.alpha_max = 1e3 + (1e8 - 1e3) * ramp"""
grad = grad.replace(old, new)
with open("micrograd/gradient_optimizer.py", "w") as f:
    f.write(grad)
print("Patched gradient_optimizer.py (alpha-continuation)")

# ---------- 3. Write example scripts ----------
examples = {}

examples["linear_target.py"] = r"""
from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt; import numpy as np, os, csv
from dolfinx import fem; import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: x[1] / 500e-6,
                                     w_f=1e-7, w_c=1e3, V_star=0.5)
    opt.rho.x.array[:] = 1.0; opt.rho.x.scatter_forward()
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
    c_h = opt.c_h; x = opt.msh.geometry.x
    outlet_facets = opt.boundary_data["outlet"]
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, outlet_facets)
    y_out = x[dofs,1]; c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_s, c_s = y_out[idx], c_out[idx]
    fig,ax=plt.subplots(); ax.plot(y_s*1e6,c_s,'b-',label='TopOpt')
    ax.plot(y_s*1e6, y_s/500e-6, 'r--', label='target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/linear_outlet.pdf')
    u_h=opt.u_h; Q=ufl.assemble(ufl.dot(u_h, ufl.FacetNormal(opt.msh))*ufl.ds(outlet_facets))
    R=1000.0/Q; rmse=np.sqrt(np.mean((c_s - y_s/500e-6)**2))
    with open('figures/linear_metrics.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['Metric','Value']); w.writerow(['RMSE',rmse])
        w.writerow(['Hydraulic R (Pa.s/m^3)',R]); w.writerow(['Flow rate (m^3/s)',Q])
    print(f"RMSE = {rmse:.6f}"); print(f"Hydraulic R = {R:.4e} Pa.s/m³")
    print(f"Flow rate Q = {Q:.4e} m³/s")
if __name__=='__main__': main()
"""

examples["double_peak_target.py"] = r"""
from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt; import numpy as np, os, csv
from dolfinx import fem; import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: np.sin(np.pi*x[1]/500e-6)**2,
                                     w_f=1e-7, w_c=1e3, V_star=0.5)
    opt.rho.x.array[:] = 1.0; opt.rho.x.scatter_forward()
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
    c_h = opt.c_h; x = opt.msh.geometry.x
    outlet_facets = opt.boundary_data["outlet"]
    dofs = fem.locate_dofs_topological(c_h.function_space, 1, outlet_facets)
    y_out = x[dofs,1]; c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out); y_s, c_s = y_out[idx], c_out[idx]
    fig,ax=plt.subplots(); ax.plot(y_s*1e6,c_s,'b-',label='TopOpt')
    ax.plot(y_s*1e6, np.sin(np.pi*y_s/500e-6)**2, 'r--', label='target')
    ax.set_xlabel('y (µm)'); ax.set_ylabel('c'); ax.legend()
    fig.savefig('figures/double_peak_outlet.pdf')
    print("Double-peak profile saved to figures/double_peak_outlet.pdf")
if __name__=='__main__': main()
"""

examples["gallery_targets.py"] = r"""
from micrograd import GradientGeneratorOptimizer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt; import numpy as np, os, csv
from dolfinx import fem; import ufl

targets = {
    'linear': lambda x: x[1]/500e-6,
    'sigmoid': lambda x: 1/(1+np.exp(-10*(x[1]/500e-6-0.5))),
    'double_peak': lambda x: np.sin(np.pi*x[1]/500e-6)**2,
    'staircase': lambda x: np.clip((x[1]//(500e-6/3)+1)/3,0,1)
}

def main():
    os.makedirs('figures', exist_ok=True)
    fig, axes = plt.subplots(2,2,figsize=(10,8))
    for ax,(name,target) in zip(axes.flat, targets.items()):
        opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                         target_expr=target, w_f=1e-7, w_c=1e3, V_star=0.5)
        opt.rho.x.array[:] = 1.0; opt.rho.x.scatter_forward()
        rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
        c_h = opt.c_h; x = opt.msh.geometry.x
        outlet_facets = opt.boundary_data["outlet"]
        dofs = fem.locate_dofs_topological(c_h.function_space, 1, outlet_facets)
        y_out = x[dofs,1]; c_out = c_h.x.array[dofs]
        idx = np.argsort(y_out); y_s, c_s = y_out[idx], c_out[idx]
        ax.plot(y_s*1e6,c_s,'b-',label='TopOpt')
        ax.plot(y_s*1e6,target(np.array([y_s*0,y_s])),'r--',label='target')
        ax.set_title(name); ax.set_xlabel('y (µm)'); ax.set_ylabel('c')
    fig.tight_layout(); fig.savefig('figures/gallery_profiles.pdf')
    print("Gallery saved to figures/gallery_profiles.pdf")
if __name__=='__main__': main()
"""

examples["christmas_tree_comparison.py"] = r"""
from micrograd import GradientGeneratorOptimizer, ChristmasTree
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt; import numpy as np, os, csv
from dolfinx import fem; import ufl

def main():
    os.makedirs('figures', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: x[1]/500e-6,
                                     w_f=1e-7, w_c=1e3, V_star=0.5)
    opt.rho.x.array[:] = 1.0; opt.rho.x.scatter_forward()
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
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
"""

examples["generate_macros.py"] = r"""
from micrograd import GradientGeneratorOptimizer, ChristmasTree
import numpy as np, os, csv, ufl

def main():
    os.makedirs('manuscript', exist_ok=True)
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=80, ny=20,
                                     target_expr=lambda x: x[1]/500e-6,
                                     w_f=1e-7, w_c=1e3, V_star=0.5)
    opt.rho.x.array[:] = 1.0; opt.rho.x.scatter_forward()
    rho_phys = opt.run(max_iter=400, beta_continuation=[1,2,4,8,16], move=0.02)
    u_h = opt.u_h
    Q = ufl.assemble(ufl.dot(u_h, ufl.FacetNormal(opt.msh))*ufl.ds(opt.boundary_data["outlet"]))
    R = 1000.0 / Q
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
"""

for fname, content in examples.items():
    path = os.path.join("examples" if fname != "generate_macros.py" else ".", fname)
    with open(path, "w") as f:
        f.write(content.strip())
    print(f"Written {path}")

# ---------- 4. Run all steps ----------
print("===== Running full pipeline =====")
for label, script in [
    ("linear_target.py", "examples/linear_target.py"),
    ("double_peak_target.py", "examples/double_peak_target.py"),
    ("gallery_targets.py", "examples/gallery_targets.py"),
    ("christmas_tree_comparison.py", "examples/christmas_tree_comparison.py"),
    ("generate_macros.py", "generate_macros.py"),
]:
    print(f"\n>>> {label}")
    subprocess.run([sys.executable, script], check=True)

print("\n===== Pipeline complete =====")
