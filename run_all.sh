#!/usr/bin/env bash
# run_all.sh — works both inside Docker (dolfinx container) and local conda env
set -euo pipefail

# Use container python3 if the conda env isn't present
if command -v conda &>/dev/null && conda env list | grep -q fenicsx; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate fenicsx
    PY="python3"
else
    PY="python3"
fi

# Install micrograd in the current environment if not already installed
$PY -m pip install -e . --no-deps -q 2>/dev/null || true

echo "============================================================"
echo " micrograd — full pipeline"
echo " Python: $($PY --version)"
echo "============================================================"

mkdir -p figures docs/si

run_script() {
    local label="$1"; local script="$2"
    echo ""
    echo ">>> $label"
    if $PY "$script"; then
        echo "    [ OK ] $label"
    else
        echo "    [WARN] $label exited non-zero — continuing"
    fi
}

run_script "[1/6] linear_target"          examples/linear_target.py
run_script "[2/6] double_peak_target"     examples/double_peak_target.py
run_script "[3/6] gallery_targets"        examples/gallery_targets.py
run_script "[4/6] christmas_tree"         examples/christmas_tree_comparison.py
run_script "[5/6] generate_macros"        generate_macros.py
echo ""
echo ">>> [6/6] convergence_study"
if python3 -m micrograd.convergence_study 2>&1; then
    echo "    [ OK ] [6/6] convergence_study"
else
    echo "    [WARN] [6/6] convergence_study exited non-zero — continuing"
fi

echo ""
echo "============================================================"
echo " All scripts finished."
echo " Figures saved in: figures/"
echo "============================================================"
