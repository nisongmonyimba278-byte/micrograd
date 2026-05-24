#!/bin/bash
export PYVISTA_OFF_SCREEN=true
export MPLBACKEND=Agg
source /home/nison/miniconda3/etc/profile.d/conda.sh
conda activate fenicsx
source /home/nison/miniconda3/etc/profile.d/conda.sh
conda activate fenicsx
cd ~/micrograd

echo "============================================================"
echo " micrograd — running scripts one by one"
echo "============================================================"

# ── 1. linear_target ─────────────────────────────────────────
echo ""
echo ">>> [1/7] linear_target.py"
/home/nison/miniconda3/envs/fenicsx/bin/python examples/linear_target.py
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 2. double_peak_target ────────────────────────────────────
echo ""
echo ">>> [2/7] double_peak_target.py"
/home/nison/miniconda3/envs/fenicsx/bin/python examples/double_peak_target.py
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 3. gallery_targets ───────────────────────────────────────
echo ""
echo ">>> [3/7] gallery_targets.py"
/home/nison/miniconda3/envs/fenicsx/bin/python examples/gallery_targets.py
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 4. christmas_tree_comparison ─────────────────────────────
echo ""
echo ">>> [4/7] christmas_tree_comparison.py"
/home/nison/miniconda3/envs/fenicsx/bin/python examples/christmas_tree_comparison.py
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 5. generate_macros ───────────────────────────────────────
echo ""
echo ">>> [5/7] generate_macros.py"
/home/nison/miniconda3/envs/fenicsx/bin/python generate_macros.py
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 6. convergence_study ─────────────────────────────────────
echo ""
echo ">>> [6/7] micrograd/convergence_study.py"
/home/nison/miniconda3/envs/fenicsx/bin/python -m micrograd.convergence_study
echo ""
echo "--- Done. Press ENTER for next script ---"
read

# ── 7. scalability ───────────────────────────────────────────
echo ""
echo ">>> [7/7] micrograd/scalability.py"
/home/nison/miniconda3/envs/fenicsx/bin/python -m micrograd.scalability
echo ""
echo "--- All scripts finished ---"
echo " Figures saved in: figures/"
echo "============================================================"
echo "Press ENTER to exit."
read