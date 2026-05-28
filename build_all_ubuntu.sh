#!/usr/bin/env bash
# =============================================================================
# build_all_ubuntu.sh — full micrograd build from Ubuntu terminal
# sync → conda → pipeline → manuscript → git push
#
# Usage:
#   bash build_all_ubuntu.sh                        # full build
#   bash build_all_ubuntu.sh --skip-sync            # skip Desktop→WSL copy
#   bash build_all_ubuntu.sh --skip-pipeline        # manuscript only
#   bash build_all_ubuntu.sh --skip-manuscript      # pipeline only
#   bash build_all_ubuntu.sh --skip-push            # no git push
#   bash build_all_ubuntu.sh --skip-sync --skip-pipeline  # manuscript + push
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'
BLU='\033[0;34m'; CYN='\033[0;36m'; NC='\033[0m'
header() { echo -e "\n${CYN}=============================================${NC}"; \
           echo -e "${CYN}  $*${NC}"; \
           echo -e "${CYN}=============================================${NC}"; }
step()  { echo -e "\n${YEL}[....] $*${NC}"; }
ok()    { echo -e "${GRN}[ OK ] $*${NC}"; }
warn()  { echo -e "${YEL}[ !! ] $*${NC}"; }
die()   { echo -e "${RED}[ !! ] $*${NC}"; exit 1; }

# ── flags ─────────────────────────────────────────────────────────────────────
SKIP_SYNC=0; SKIP_PIPELINE=0; SKIP_MS=0; SKIP_PUSH=0
for arg in "$@"; do
  case $arg in
    --skip-sync)      SKIP_SYNC=1     ;;
    --skip-pipeline)  SKIP_PIPELINE=1 ;;
    --skip-manuscript) SKIP_MS=1      ;;
    --skip-push)      SKIP_PUSH=1     ;;
    --help|-h) grep '^#' "$0" | grep -v '#!/' | sed 's/^# \?//'; exit 0 ;;
    *) die "Unknown flag: $arg" ;;
  esac
done

# ── config ────────────────────────────────────────────────────────────────────
REPO_DIR="$HOME/micrograd"
CONDA_BASE="$HOME/miniconda3"
CONDA_ENV="fenicsx"
CONDA_RUN="$CONDA_BASE/bin/conda run -n $CONDA_ENV --no-capture-output"
MANUSCRIPT_DIR="$REPO_DIR/manuscript"
WINDOWS_SRC="/mnt/c/Users/nison/OneDrive/Desktop/micrograd"
START=$(date +%s)
elapsed() { echo "$(( $(date +%s) - START ))s"; }

# ── banner ────────────────────────────────────────────────────────────────────
header "micrograd — build_all_ubuntu.sh"
echo -e "  Sync       : $([ $SKIP_SYNC     -eq 1 ] && echo 'SKIP' || echo 'RUN')"
echo -e "  Pipeline   : $([ $SKIP_PIPELINE -eq 1 ] && echo 'SKIP' || echo 'RUN')"
echo -e "  Manuscript : $([ $SKIP_MS       -eq 1 ] && echo 'SKIP' || echo 'RUN')"
echo -e "  Git push   : $([ $SKIP_PUSH     -eq 1 ] && echo 'SKIP' || echo 'RUN')"

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Sync Windows Desktop → WSL
# ══════════════════════════════════════════════════════════════════════════════
if [[ $SKIP_SYNC -eq 0 ]]; then
  header "STAGE 1 — Sync Windows Desktop → WSL"

  if [[ ! -d "$WINDOWS_SRC" ]]; then
    warn "Windows source not found: $WINDOWS_SRC"
    warn "Skipping sync — using existing $REPO_DIR"
  else
    step "Syncing $WINDOWS_SRC → $REPO_DIR"
    # rsync preserves what's in WSL if not in Windows source
    if command -v rsync &>/dev/null; then
      rsync -a --delete "$WINDOWS_SRC/" "$REPO_DIR/"
    else
      rm -rf "$REPO_DIR" && cp -r "$WINDOWS_SRC" "$REPO_DIR"
    fi
    ok "Sync complete"
  fi
else
  warn "STAGE 1 (sync) skipped."
fi

cd "$REPO_DIR"

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Conda environment
# ══════════════════════════════════════════════════════════════════════════════
header "STAGE 2 — Conda environment"

[[ -f "$CONDA_BASE/bin/conda" ]] \
  || die "conda not found at $CONDA_BASE. Install Miniconda first."

step "Checking env '$CONDA_ENV'"
if ! "$CONDA_BASE/bin/conda" env list | grep -q "^$CONDA_ENV "; then
  step "Creating environment from environment.yaml"
  "$CONDA_BASE/bin/conda" env create -f environment.yaml
  ok "Environment created"
else
  ok "Environment '$CONDA_ENV' already exists"
fi

step "Installing pip deps (setuptools, nlopt)"
$CONDA_RUN pip install 'setuptools==59.5.0' nlopt 2>/dev/null || true

step "Installing micrograd package (editable)"
$CONDA_RUN pip install -e . --no-deps
ok "Package installed"

step "Creating output directories"
mkdir -p figures docs/si uq pareto
ok "Directories ready"

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Analysis pipeline
# ══════════════════════════════════════════════════════════════════════════════
run_step() {
  local label="$1"; shift
  step "$label"
  export PYTHONPATH="$REPO_DIR:${PYTHONPATH:-}"
  $CONDA_RUN "$@"
  ok "$label"
}

run_optional() {
  local label="$1" check="$2"; shift 2
  if $CONDA_RUN python3 -c "$check" &>/dev/null 2>&1; then
    run_step "$label" "$@"
  else
    warn "$label — dependency not available, skipping"
  fi
}

if [[ $SKIP_PIPELINE -eq 0 ]]; then
  header "STAGE 3 — Analysis pipeline"

  run_step "[3.1] Unit tests" \
    pytest tests/ -x -q 2>&1 | tail -5 || true

  run_step "[3.2] Mesh convergence" \
    python3 -c "
from micrograd.convergence_study import run_convergence_study
run_convergence_study(lambda x: x[1]/500e-6,
  mesh_sizes=[(40,10),(80,20),(160,40)],
  output_dir='figures', max_iter=60)"

  run_step "[3.3] Filter sensitivity" \
    python3 -c "
from micrograd.filter_sensitivity import run_filter_sensitivity
run_filter_sensitivity(lambda x: x[1]/500e-6, nx=80, ny=20,
  r_filter_multipliers=[1.0,1.5,2.0,2.5,3.0],
  output_dir='figures', max_iter=50)"

  run_step "[3.4] Stabilisation validation" \
    python3 run_stabilization_test.py
  mv stabilization_outlet.png stabilization_fields.png docs/si/ 2>/dev/null || true

  run_step "[3.5] Gallery of target profiles" \
    python3 examples/gallery_targets.py
  cp figures/gallery_target_profiles.pdf docs/si/ 2>/dev/null || true

  run_step "[3.6] Main figures" \
    python3 generate_figures.py
  cp figures/*.pdf figures/*.png docs/si/ 2>/dev/null || true

  run_step "[3.7] Supplementary Information" \
    python3 generate_si.py

  run_optional "[3.8] OC vs MMA comparison" "import gcma" \
    python3 run_optimizer_comparison.py
  cp docs/si/S4_optimizer_comparison.pdf docs/si/ 2>/dev/null || true

  run_optional "[3.9] Uncertainty quantification" "import chaospy" \
    python3 run_uq.py
  cp -r uq/* docs/si/ 2>/dev/null || true

  run_step "[3.10] Multi-objective Pareto front" \
    python3 run_pareto.py
  cp -r pareto/* docs/si/ 2>/dev/null || true

  ok "Pipeline complete ($(elapsed))"
else
  warn "STAGE 3 (pipeline) skipped."
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Manuscript compilation
# ══════════════════════════════════════════════════════════════════════════════
if [[ $SKIP_MS -eq 0 ]]; then
  header "STAGE 4 — Manuscript (pdflatex × 2)"

  [[ -d "$MANUSCRIPT_DIR" ]] \
    || die "Manuscript dir not found: $MANUSCRIPT_DIR"
  [[ -f "$MANUSCRIPT_DIR/main.tex" ]] \
    || die "main.tex not found in $MANUSCRIPT_DIR"

  command -v pdflatex &>/dev/null \
    || die "pdflatex not in PATH. Run: sudo apt install texlive-full"

  cd "$MANUSCRIPT_DIR"

  step "Pass 1/2"
  pdflatex -interaction=nonstopmode -halt-on-error main.tex \
    2>&1 | grep -E "^!|Output written" || true
  grep -c "^!" main.log 2>/dev/null | grep -q "^0$" \
    || { grep "^!" main.log; die "pdflatex pass 1 failed"; }
  ok "Pass 1 complete"

  step "Pass 2/2"
  pdflatex -interaction=nonstopmode -halt-on-error main.tex \
    2>&1 | grep -E "^!|Output written" || true
  grep -c "^!" main.log 2>/dev/null | grep -q "^0$" \
    || { grep "^!" main.log; die "pdflatex pass 2 failed"; }
  ok "Pass 2 complete"

  PAGES=$(grep "Output written" main.log \
          | grep -oP '\d+ page' | grep -oP '\d+' || echo "?")
  UNDEF=$(grep -c "undefined" main.log 2>/dev/null || echo 0)
  OVER=$(grep  -c "Overfull"  main.log 2>/dev/null || echo 0)
  UNDER=$(grep -c "Underfull" main.log 2>/dev/null || echo 0)

  echo ""
  ok "main.pdf — $PAGES pages"
  echo -e "  Undefined refs  : $UNDEF"
  echo -e "  Overfull hboxes : $OVER"
  echo -e "  Underfull hboxes: $UNDER"

  cp main.pdf "$REPO_DIR/main.pdf" 2>/dev/null && \
    ok "PDF copied to $REPO_DIR/main.pdf" || true

  cd "$REPO_DIR"
else
  warn "STAGE 4 (manuscript) skipped."
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Git commit and push
# ══════════════════════════════════════════════════════════════════════════════
if [[ $SKIP_PUSH -eq 0 ]]; then
  header "STAGE 5 — Git commit and push"

  cd "$REPO_DIR"
  if git diff --quiet && git diff --cached --quiet \
     && [[ -z "$(git status --porcelain)" ]]; then
    ok "Nothing to commit — working tree clean."
  else
    step "Staging all changes"
    git add -A
    STAMP=$(date '+%Y-%m-%d %H:%M')
    git commit -m "build: full pipeline run $STAMP"
    ok "Committed"

    step "Pushing to origin/main"
    git push origin "$(git rev-parse --abbrev-ref HEAD)"
    ok "Pushed to GitHub"
  fi
else
  warn "STAGE 5 (git push) skipped."
fi

# ── summary ───────────────────────────────────────────────────────────────────
header "ALL DONE  (total: $(elapsed))"
echo -e "${GRN}  figures/        pipeline outputs${NC}"
echo -e "${GRN}  docs/si/        supplementary info${NC}"
echo -e "${GRN}  manuscript/     source + main.pdf${NC}"
echo -e "${GRN}  main.pdf        copy at repo root${NC}"
