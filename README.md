markdown
# micrograd – Topology optimisation of microfluidic gradient generators

[![CI](https://github.com/yourusername/micrograd/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/micrograd/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

**Automated inverse design of microfluidic concentration gradient generators for arbitrary outlet profiles.**

<p align="center">
  <img src="docs/si/S12_gallery.pdf" width="800" alt="Gallery of target profiles">
</p>

---

## What does this do?

Given a **desired concentration profile** at the outlet of a microfluidic chip, this framework automatically discovers the channel geometry that produces it – with **no pre‑prescribed architecture**.  The optimised designs outperform the classic “Christmas tree” generator by **~50 % in hydraulic resistance** while maintaining superior concentration fidelity.

The code solves a density‑based topology optimisation problem with coupled Brinkman flow and convection‑diffusion, uses continuous adjoint sensitivity for efficient gradient computation, and validates the results with full Navier–Stokes simulations and 3D extrusion.

---

## Installation & reproduction

Choose the method that best fits your operating system.

### Option 1 – Docker (recommended for Windows, works everywhere)

This method uses a pre‑built FEniCSx Docker image that already contains **all** dependencies (FEniCSx, PETSc, MPI, Gmsh, PyVista).  No Conda or manual setup is needed.

1. **Install Docker Desktop**  
   Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your operating system.  
   *If Docker is missing, the reproduction script can install it automatically on Windows via `winget` or the official installer.*

2. **Run the pipeline**  
   Open a terminal (PowerShell on Windows, bash on Linux/macOS) in the `micrograd` folder and execute:

   ```bash
   # Windows PowerShell
   .\run_docker.ps1
   
   # Linux / macOS (bash)
   bash run_docker.sh
This single command will:

Pull the official dolfinx/dolfinx image.

Install micrograd and optional packages (gcma, chaospy) inside a container.

Execute every analysis script in the correct order (unit tests → mesh convergence → filter sensitivity → … → Pareto sweep).

Collect all figures, tables, and the Supplementary Information package into your figures/ and docs/si/ folders.

Stop and remove the container when finished.

All outputs appear directly on your machine – no file copying needed.

Option 2 – Conda (native Linux / macOS / Windows)
If you already have Conda installed and prefer a native environment:

Create the environment

bash
conda env create -f environment.yaml
conda activate micrograd-env
pip install -e .
Run the complete reproduction

bash
# Windows PowerShell
.\run_all.ps1

# Linux / macOS (if you create a bash equivalent – see run_all.sh)
bash run_all.sh
The script will detect missing optional packages (gcma, chaospy) and skip the corresponding steps gracefully.

Quick start
After installing the package, you can run a single optimisation in a few lines:

python
from micrograd import GradientGeneratorOptimizer

# Target a linear gradient from 0 to 1 across the 500 µm outlet
opt = GradientGeneratorOptimizer(
    target_expr=lambda x: x[1] / 500e-6,
    Lx=2000e-6, Ly=500e-6, nx=80, ny=20
)
opt.run(max_iter=80)
opt.plot()
opt.export_stl("my_channel.stl")
Jupyter notebook available at notebooks/topopt_gradient_generator.ipynb.

What the reproduction pipeline runs
Step	Description	Output
1	Core unit tests	pytest output
2	Mesh convergence study	figures/convergence_*.png, figures/convergence_metrics.csv
3	Filter radius sensitivity	figures/filter_*.png, figures/filter_metrics.csv
4	Stabilisation validation	docs/si/S3_stabilization_outlet.pdf, S3_stabilization_rmse.csv
5	Gallery of target profiles	figures/gallery_target_profiles.pdf
6	Main figures (linear + Christmas tree + 3D)	figures/outlet_profile.pdf, figures/bar_chart_resistance.pdf, figures/3d_channel_render.png, …
7	Supplementary Information package	docs/si/ – all figures, tables, CSVs
8	OC vs. MMA comparison	docs/si/S4_optimizer_comparison.pdf, S4_comparison.csv
9	Uncertainty quantification (polynomial chaos)	uq/uq_outlet_envelope.pdf, uq_mean_profile.csv
10	Multi‑objective Pareto front	pareto/pareto_resistance_vs_rmse.pdf, pareto_data.csv
11	Full test suite	pytest tests/ -v
All files are placed directly into the repository structure – no extra export steps required.

Key features
Density‑based topology optimisation – coupled Brinkman (Darcy) flow + convection‑diffusion

Continuous adjoint sensitivity – cheap gradient computation independent of design variables

Design regularisation – Helmholtz PDE filter & smooth Heaviside projection

Optimisation algorithms – Optimality Criteria (OC) & Method of Moving Asymptotes (MMA)

Continuation strategies – volume fraction (0.7→0.5) and Heaviside sharpening (β 1→16)

Navier–Stokes validation – body‑fitted remeshing (Gmsh) with full NS simulation

3D extrusion & validation – 3D Navier–Stokes on extruded channel

Uncertainty quantification – polynomial chaos expansion for fabrication robustness (±10 % width)

Multi‑objective Pareto front – trade‑off between pressure drop and concentration error

Manufacturability checks – minimum feature size (distance transform) against 10 µm lithography limit

Christmas tree generator – direct comparison with Jeon et al. (2005)

Fully open‑source – MIT license, CI‑tested, pip‑installable, Jupyter notebook included

Project structure
text
micrograd/
├── micrograd/                 # Core package
│   ├── solver.py              # Brinkman + convection‑diffusion forward solver
│   ├── adjoint.py             # Continuous adjoint and sensitivity
│   ├── optimizer.py           # OC & MMA updaters
│   ├── gradient_optimizer.py  # Main topology optimisation class
│   ├── validation.py          # Navier–Stokes validation, metrics
│   ├── validation_3d.py       # 3D extrusion & validation
│   ├── experimental_metrics.py# Pressure drop, Re, Pe, mixing length, …
│   ├── manufacturability.py   # Min feature size, robust projection
│   ├── christmas_tree.py      # Christmas tree simulator
│   ├── uncertainty_quantification.py  # PCE‑based UQ
│   ├── multiobjective.py      # Pareto sweep
│   └── … (mesh, utilities, postprocess, etc.)
├── examples/                  # Standalone examples
├── tests/                     # Unit tests (pytest)
├── notebooks/                 # Jupyter notebook demo
├── docs/                      # Sphinx documentation + SI
├── manuscript/                # LaTeX manuscript + figures
├── presentation/              # Beamer slide deck
├── run_all.ps1               # Native Conda pipeline (Windows)
├── run_docker.ps1            # Docker pipeline (Windows, auto‑installs Docker)
├── environment.yaml           # Exact Conda environment
├── setup.py                   # pip‑installable package
└── README.md
Documentation
API Reference – https://micrograd.readthedocs.io (autogenerated from docstrings)

Supplementary Information – https://yourusername.github.io/micrograd/si/

Manuscript draft – manuscript/manuscript.pdf

Citing this work
If you use micrograd in your research, please cite:

bibtex
@article{monyimba2025micrograd,
  title   = {Topology optimisation of microfluidic concentration gradient generators
             for arbitrary outlet profiles},
  author  = {Monyimba, Nisong},
  year    = {2025},
  journal = {in preparation}
}
The code is permanently archived on Zenodo with DOI 10.5281/zenodo.XXXXXXX.

License
MIT – see LICENSE file.

Contributing
Contributions are welcome! Please open an issue or pull request on GitHub. For major changes, please discuss them first.

Contact
Nisong Monyimba – nmonyimb@asu.edu
GitHub: https://github.com/yourusername/micrograd

text
