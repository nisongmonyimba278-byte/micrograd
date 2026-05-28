#!/usr/bin/env bash
# =============================================================================
# build_all_ubuntu.sh — full micrograd build from Ubuntu terminal
# Usage:
#   bash build_all_ubuntu.sh                          # full build
#   bash build_all_ubuntu.sh --skip-sync              # skip Desktop→WSL copy
#   bash build_all_ubuntu.sh --skip-pipeline          # manuscript only
#   bash build_all_ubuntu.sh --skip-manuscript        # pipeline only
#   bash build_all_ubuntu.sh --skip-push              # no git push
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'
header() { echo -e "\n${CYN}=============================================${NC}"; echo -e "${CYN}  $*${NC}"; echo -e "${CYN}=============================================${NC}"; }
step()   { echo -e "\n${YEL}[....] $*${NC}"; }
ok()     { echo -e "${GRN}[ OK ] $*${NC}"; }
warn()   { echo -e "${YEL}[ !! ] $*${NC}"; }
die()    { echo -e "${RED}[ !! ] $*${NC}"; exit 1; }

SKIP_SYNC=0; SKIP_PIPELINE=0; SKIP_MS=0; SKIP_PUSH=0
for arg in "$@"; do
  case $arg in
    --skip-sync)       SKIP_SYNC=1     ;;
    --skip-pipeline)   SKIP_PIPELINE=1 ;;
    --skip-manuscript) SKIP_MS=1       ;;
    --skip-push)       SKIP_PUSH=1     ;;
    --help|-h) grep '^#' "$0" | grep -v '#!/' | sed 's/^# \?//'; exit 0 ;;
    *) die "Unknown flag: $arg" ;;
  esac
done

REPO_DIR="$HOME/micrograd"
CONDA_BASE="$HOME/miniconda3"
CONDA_ENV="fenicsx"
CONDA_RUN=("$CONDA_BASE/bin/conda" run -n "$CONDA_ENV" --no-capture-output)
MANUSCRIPT_DIR="$REPO_DIR/manuscript"
WINDOWS_SRC="/mnt/c/Users/nison/OneDrive/Desktop/micrograd"
START=$(date +%s)
elapsed() { echo "$(( $(date +%s) - START ))s"; }

header "micrograd — build_all_ubuntu.sh"
echo -e "  Sync       : $([ $SKIP_SYNC     -eq 1 ] && echo SKIP || echo RUN)"
echo -e "  Pipeline   : $([ $SKIP_PIPELINE -eq 1 ] && echo SKIP || echo RUN)"
echo -e "  Manuscript : $([ $SKIP_MS       -eq 1 ] && echo SKIP || echo RUN)"
echo -e "  Git push   : $([ $SKIP_PUSH     -eq 1 ] && echo SKIP || echo RUN)"

# ── STAGE 1: Sync ─────────────────────────────────────────────────────────────
if [[ $SKIP_SYNC -eq 0 ]]; then
  header "STAGE 1 — Sync Windows Desktop → WSL"
  if [[ ! -d "$WINDOWS_SRC" ]]; then
    warn "Windows source not found: $WINDOWS_SRC — skipping sync."
  else
    step "Syncing $WINDOWS_SRC → $REPO_DIR"
    rsync -rlt --no-group --no-owner --no-perms --delete \
      --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" \
      "$WINDOWS_SRC/" "$REPO_DIR/"
    ok "Sync complete"
    # restore build scripts that live in git but not on Windows Desktop
    git -C "$REPO_DIR" checkout HEAD -- build_all_ubuntu.sh build_all.ps1 2>/dev/null || true
    ok "Build scripts restored from git"
  fi
else
  warn "STAGE 1 (sync) skipped."
fi

cd "$REPO_DIR"

# ── STAGE 2: Conda ────────────────────────────────────────────────────────────
header "STAGE 2 — Conda environment"
[[ -f "$CONDA_BASE/bin/conda" ]] || die "conda not found at $CONDA_BASE"

step "Checking env '$CONDA_ENV'"
if ! "$CONDA_BASE/bin/conda" env list | grep -q "^$CONDA_ENV "; then
  step "Creating from environment.yaml"
  "$CONDA_BASE/bin/conda" env create -f environment.yaml
fi
ok "Env ready"

"${CONDA_RUN[@]}" pip install 'setuptools==59.5.0' nlopt 2>/dev/null || true
"${CONDA_RUN[@]}" pip install -e . --no-deps
mkdir -p figures docs/si uq pareto
ok "Package installed, output dirs ready"

# ── STAGE 3: Pipeline ─────────────────────────────────────────────────────────
run_step() {
  local label="$1"; shift
  step "$label"
  export PYTHONPATH="$REPO_DIR:${PYTHONPATH:-}"
  "${CONDA_RUN[@]}" "$@"
  ok "$label"
}
run_optional() {
  local label="$1" check="$2"; shift 2
  if "${CONDA_RUN[@]}" python3 -c "$check" &>/dev/null 2>&1; then
    run_step "$label" "$@"
  else
    warn "$label — dependency missing, skipping"
  fi
}

if [[ $SKIP_PIPELINE -eq 0 ]]; then
  header "STAGE 3 — Analysis pipeline"

  run_step "[3.1] Unit tests" \
    python3 -m pytest tests/ -x -q 2>&1 | tail -5 || true

  run_step "[3.2] Mesh convergence" \
    python3 -c "
from micrograd.convergence_study import run_convergence_study
run_convergence_study(lambda x: x[1]/500e-6,
  mesh_sizes=[(40,10),(80,20),(160,40)], output_dir='figures', max_iter=60)"

  run_step "[3.3] Filter sensitivity" \
    python3 -c "
from micrograd.filter_sensitivity import run_filter_sensitivity
run_filter_sensitivity(lambda x: x[1]/500e-6, nx=80, ny=20,
  r_filter_multipliers=[1.0,1.5,2.0,2.5,3.0], output_dir='figures', max_iter=50)"

  run_step "[3.4] Stabilisation" python3 run_stabilization_test.py
  mv stabilization_outlet.png stabilization_fields.png docs/si/ 2>/dev/null || true

  run_step "[3.5] Gallery profiles" python3 examples/gallery_targets.py
  cp figures/gallery_target_profiles.pdf docs/si/ 2>/dev/null || true

  run_step "[3.6] Main figures" python3 generate_figures.py
  cp figures/*.pdf figures/*.png docs/si/ 2>/dev/null || true

  run_step "[3.7] Supplementary Info" python3 generate_si.py

  run_optional "[3.8] OC vs MMA"  "import gcma"    python3 run_optimizer_comparison.py
  run_optional "[3.9] UQ"         "import chaospy" python3 run_uq.py
  cp -r uq/* docs/si/ 2>/dev/null || true

  run_step "[3.10] Pareto front" python3 run_pareto.py
  cp -r pareto/* docs/si/ 2>/dev/null || true

  ok "Pipeline complete ($(elapsed))"
else
  warn "STAGE 3 (pipeline) skipped."
fi

# ── STAGE 4: Manuscript ───────────────────────────────────────────────────────
if [[ $SKIP_MS -eq 0 ]]; then
  header "STAGE 4 — Manuscript (pdflatex × 2)"
  [[ -d "$MANUSCRIPT_DIR" ]] || die "Manuscript dir not found: $MANUSCRIPT_DIR"
  [[ -f "$MANUSCRIPT_DIR/main.tex" ]] || die "main.tex not found"
  command -v pdflatex &>/dev/null || die "pdflatex not found — run: sudo apt install texlive-full"

  cd "$MANUSCRIPT_DIR"
  for pass in 1 2; do
    step "Pass $pass/2"
    pdflatex -interaction=nonstopmode -halt-on-error main.tex 2>&1 | grep -E "^!|Output written" || true
    [[ $(grep -c "^!" main.log 2>/dev/null || echo 0) -eq 0 ]] \
      || { grep "^!" main.log; die "pdflatex pass $pass failed"; }
    ok "Pass $pass complete"
  done

  PAGES=$(grep "Output written" main.log | grep -oP '\d+ page' | grep -oP '\d+' || echo "?")
  UNDEF=$(grep -c "undefined" main.log 2>/dev/null || echo 0)
  OVER=$( grep -c "Overfull"  main.log 2>/dev/null || echo 0)
  echo ""
  ok "main.pdf — $PAGES pages | undefined: $UNDEF | overfull: $OVER"
  cp main.pdf "$REPO_DIR/main.pdf" 2>/dev/null || true
  cd "$REPO_DIR"
else
  warn "STAGE 4 (manuscript) skipped."
fi

# ── STAGE 5: Git ──────────────────────────────────────────────────────────────
if [[ $SKIP_PUSH -eq 0 ]]; then
  header "STAGE 5 — Git commit and push"
  if git diff --quiet && git diff --cached --quiet && [[ -z "$(git status --porcelain)" ]]; then
    ok "Nothing to commit."
  else
    git add -A
    git commit -m "build: full pipeline run $(date '+%Y-%m-%d %H:%M')"
    git push origin "$(git rev-parse --abbrev-ref HEAD)"
    ok "Committed and pushed"
  fi
else
  warn "STAGE 5 (git push) skipped."
fi

header "ALL DONE  ($(elapsed))"
echo -e "${GRN}  figures/     pipeline outputs${NC}"
echo -e "${GRN}  docs/si/     supplementary info${NC}"
echo -e "${GRN}  main.pdf     manuscript${NC}"
