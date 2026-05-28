#!/usr/bin/env bash
# run_manuscript.sh – generate all outputs & compile the manuscript
set -euo pipefail

PROJECT_DIR="${HOME}/micrograd"
MANUSCRIPT_DIR="${PROJECT_DIR}/manuscript"
FIGURES_DIR="${PROJECT_DIR}/figures"

echo "========================================="
echo " micrograd manuscript compilation script "
echo "========================================="

# ----------------------------------------------------------------------
# 1. Run the full pipeline (generates figures, macros, etc.)
# ----------------------------------------------------------------------
echo ""
echo "Step 1/2: Running full pipeline (bash run_all.sh) ..."
cd "${PROJECT_DIR}"
if [ -f run_all.sh ]; then
    bash run_all.sh
else
    echo "ERROR: run_all.sh not found in ${PROJECT_DIR}"
    exit 1
fi

# ----------------------------------------------------------------------
# 2. Verify that mandatory files exist
# ----------------------------------------------------------------------
echo ""
echo "Step 2/2: Verifying generated files..."

MANDATORY_FILES=(
    "${MANUSCRIPT_DIR}/macros.tex"
    "${FIGURES_DIR}/comparison.pdf"
    "${FIGURES_DIR}/gallery_profiles.pdf"
    "${FIGURES_DIR}/topology_optimised.pdf"
    #"${FIGURES_DIR}/linear_outlet.pdf"
)
MISSING=0
for f in "${MANDATORY_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "   MISSING: $f"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo "ERROR: Some required files are missing. Please check the pipeline output."
    exit 1
else
    echo "   All mandatory files present."
fi

# ----------------------------------------------------------------------
# 3. Compile the manuscript (pdflatex → bibtex → pdflatex → pdflatex)
# ----------------------------------------------------------------------
if ! command -v pdflatex &> /dev/null; then
    echo ""
    echo "LaTeX not found. Installing texlive-latex-recommended and texlive-bibtex-extra..."
    sudo apt update && sudo apt install -y texlive-latex-recommended texlive-bibtex-extra
fi

cd "${MANUSCRIPT_DIR}"

echo ""
echo "Compiling manuscript (1/3) ..."
pdflatex -interaction=nonstopmode main.tex

echo "Running bibtex ..."
echo "Skipping bibtex (thebibliography used)"

echo "Compiling manuscript (2/3) ..."
pdflatex -interaction=nonstopmode main.tex

echo "Compiling manuscript (3/3) ..."
pdflatex -interaction=nonstopmode main.tex

# ----------------------------------------------------------------------
# 4. Final check
# ----------------------------------------------------------------------
if [ -f main.pdf ]; then
    echo ""
    echo "========================================="
    echo "  Manuscript successfully compiled!      "
    echo "  Output: ${MANUSCRIPT_DIR}/main.pdf     "
    echo "========================================="
else
    echo "ERROR: main.pdf not generated. Check main.log for details."
    exit 1
fi
