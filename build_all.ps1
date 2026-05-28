# =============================================================================
# build_all.ps1 — sync + conda + pipeline + manuscript + git push
# Usage:
#   powershell -ExecutionPolicy Bypass -File build_all.ps1
#   powershell -ExecutionPolicy Bypass -File build_all.ps1 -SkipSync
#   powershell -ExecutionPolicy Bypass -File build_all.ps1 -SkipPipeline
#   powershell -ExecutionPolicy Bypass -File build_all.ps1 -SkipManuscript
#   powershell -ExecutionPolicy Bypass -File build_all.ps1 -SkipPush
# =============================================================================
param(
    [switch]$SkipSync,
    [switch]$SkipPipeline,
    [switch]$SkipManuscript,
    [switch]$SkipPush
)
$ErrorActionPreference = "Stop"
$StartTime = Get-Date

$wslDistro     = "Ubuntu"
$condaBase     = "/home/nison/miniconda3"
$condaEnv      = "fenicsx"
$remoteDir     = "/home/nison/micrograd"
$windowsSrc    = "C:\Users\nison\OneDrive\Desktop\micrograd"
$condaRun      = "$condaBase/bin/conda run -n $condaEnv --no-capture-output"
$manuscriptDir = "$remoteDir/manuscript"

function Header([string]$m) {
    Write-Host "`n=============================================" -ForegroundColor Cyan
    Write-Host "  $m" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
}
function Step([string]$m)  { Write-Host "`n[....] $m" -ForegroundColor Yellow }
function OK([string]$m)    { Write-Host "[ OK ] $m"  -ForegroundColor Green  }
function Warn([string]$m)  { Write-Host "[ !! ] $m"  -ForegroundColor Yellow }
function Elapsed { return "$([int](New-TimeSpan -Start $StartTime -End (Get-Date)).TotalSeconds)s" }

function Invoke-WSL([string]$cmd, [string]$label) {
    Step $label
    $full = "cd $remoteDir && export PYTHONPATH=${remoteDir}:" + '${PYTHONPATH} && ' + "$condaRun $cmd"
    wsl -d $wslDistro -- bash -c $full
    if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: $label"; exit $LASTEXITCODE }
    OK $label
}
function Invoke-WSL-Optional([string]$cmd, [string]$check, [string]$label) {
    wsl -d $wslDistro -- bash -c "$condaRun python3 -c '$check'" 2>$null
    if ($LASTEXITCODE -eq 0) { Invoke-WSL $cmd $label }
    else { Warn "$label — dependency missing, skipping." }
}

Header "micrograd — build_all.ps1"
Write-Host "  Sync      : $(if($SkipSync)     {'SKIP'} else {'RUN'})"
Write-Host "  Pipeline  : $(if($SkipPipeline) {'SKIP'} else {'RUN'})"
Write-Host "  Manuscript: $(if($SkipManuscript){'SKIP'} else {'RUN'})"
Write-Host "  Git push  : $(if($SkipPush)     {'SKIP'} else {'RUN'})"

Step "Checking WSL"
$wslList = wsl --list --verbose 2>&1 | Out-String
if ($wslList -notmatch $wslDistro) { Write-Error "WSL distro '$wslDistro' not found"; exit 1 }
OK "WSL $wslDistro found"

# ── STAGE 1: Sync ─────────────────────────────────────────────────────────────
if (-not $SkipSync) {
    Header "STAGE 1 — Sync Windows Desktop → WSL"
    if (-not (Test-Path $windowsSrc)) {
        Warn "Source not found: $windowsSrc — skipping sync."
    } else {
        Step "Syncing $windowsSrc → $remoteDir"
        $srcWSL = ($windowsSrc -replace '\\','/') -replace 'C:','/mnt/c'
        wsl -d $wslDistro -- bash -c "rm -rf $remoteDir && cp -r '$srcWSL' $remoteDir"
        if ($LASTEXITCODE -ne 0) { Write-Error "Sync failed"; exit 1 }
        OK "Sync complete"
    }
} else { Warn "STAGE 1 skipped." }

# ── STAGE 2: Conda ────────────────────────────────────────────────────────────
Header "STAGE 2 — Conda environment"
Step "Checking env '$condaEnv'"
$envList = wsl -d $wslDistro -- bash -c "$condaBase/bin/conda env list 2>&1"
if ($envList -notmatch $condaEnv) {
    Step "Creating from environment.yaml"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && $condaBase/bin/conda env create -f environment.yaml"
}
OK "Env ready"
wsl -d $wslDistro -- bash -c "$condaRun pip install 'setuptools==59.5.0' nlopt 2>/dev/null || true"
wsl -d $wslDistro -- bash -c "cd $remoteDir && $condaRun pip install -e . --no-deps"
wsl -d $wslDistro -- bash -c "mkdir -p $remoteDir/figures $remoteDir/docs/si $remoteDir/uq $remoteDir/pareto"
OK "Package installed, output dirs ready"

# ── STAGE 3: Pipeline ─────────────────────────────────────────────────────────
if (-not $SkipPipeline) {
    Header "STAGE 3 — Analysis pipeline"

    Invoke-WSL "pytest tests/ -x -q 2>&1 | tail -5" "[3.1] Unit tests"

    Invoke-WSL ("python3 -c 'from micrograd.convergence_study import run_convergence_study; " +
        "run_convergence_study(lambda x: x[1]/500e-6, mesh_sizes=[(40,10),(80,20),(160,40)], " +
        "output_dir=\"figures\", max_iter=60)'") "[3.2] Mesh convergence"

    Invoke-WSL ("python3 -c 'from micrograd.filter_sensitivity import run_filter_sensitivity; " +
        "run_filter_sensitivity(lambda x: x[1]/500e-6, nx=80, ny=20, " +
        "r_filter_multipliers=[1.0,1.5,2.0,2.5,3.0], output_dir=\"figures\", max_iter=50)'") "[3.3] Filter sensitivity"

    Invoke-WSL "python3 run_stabilization_test.py" "[3.4] Stabilisation"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && mv stabilization_outlet.png stabilization_fields.png docs/si/ 2>/dev/null; true"

    Invoke-WSL "python3 examples/gallery_targets.py"  "[3.5] Gallery profiles"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp figures/gallery_target_profiles.pdf docs/si/ 2>/dev/null; true"

    Invoke-WSL "python3 generate_figures.py"           "[3.6] Main figures"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp figures/*.pdf figures/*.png docs/si/ 2>/dev/null; true"

    Invoke-WSL "python3 generate_si.py"                "[3.7] Supplementary Info"

    Invoke-WSL-Optional "python3 run_optimizer_comparison.py" "import gcma"    "[3.8] OC vs MMA"
    Invoke-WSL-Optional "python3 run_uq.py"                   "import chaospy" "[3.9] UQ"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp -r uq/* docs/si/ 2>/dev/null; true"

    Invoke-WSL "python3 run_pareto.py" "[3.10] Pareto front"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp -r pareto/* docs/si/ 2>/dev/null; true"

    OK "Pipeline complete ($(Elapsed))"
} else { Warn "STAGE 3 skipped." }

# ── STAGE 4: Manuscript ───────────────────────────────────────────────────────
if (-not $SkipManuscript) {
    Header "STAGE 4 — Manuscript (pdflatex x2)"

    Step "Checking pdflatex"
    $pdf = wsl -d $wslDistro -- bash -c "command -v pdflatex 2>/dev/null || echo MISSING"
    if ($pdf -match "MISSING") { Write-Error "pdflatex not found in WSL. Run: sudo apt install texlive-full"; exit 1 }
    OK "pdflatex found"

    Step "Pass 1/2"
    wsl -d $wslDistro -- bash -c "cd $manuscriptDir && pdflatex -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tail -3"
    if ($LASTEXITCODE -ne 0) { Write-Error "pdflatex pass 1 failed"; exit 1 }
    OK "Pass 1 done"

    Step "Pass 2/2"
    wsl -d $wslDistro -- bash -c "cd $manuscriptDir && pdflatex -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tail -3"
    if ($LASTEXITCODE -ne 0) { Write-Error "pdflatex pass 2 failed"; exit 1 }
    OK "Pass 2 done"

    $stats = wsl -d $wslDistro -- bash -c @"
L=$manuscriptDir/main.log
printf 'pages=%s undef=%s over=%s under=%s' \
  `$(grep 'Output written' `$L | grep -oP '\d+ page' | grep -oP '\d+' || echo '?')` \
  `$(grep -c 'undefined' `$L 2>/dev/null || echo 0)` \
  `$(grep -c 'Overfull'  `$L 2>/dev/null || echo 0)` \
  `$(grep -c 'Underfull' `$L 2>/dev/null || echo 0)`
"@
    Write-Host "`n  $stats" -ForegroundColor Green

    wsl -d $wslDistro -- bash -c "cp $manuscriptDir/main.pdf $remoteDir/main.pdf 2>/dev/null; true"
    OK "PDF copied to $remoteDir/main.pdf"
} else { Warn "STAGE 4 skipped." }

# ── STAGE 5: Git ──────────────────────────────────────────────────────────────
if (-not $SkipPush) {
    Header "STAGE 5 — Git commit and push"
    $dirty = wsl -d $wslDistro -- bash -c "cd $remoteDir && git status --porcelain"
    if ([string]::IsNullOrWhiteSpace($dirty)) {
        OK "Nothing to commit."
    } else {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        wsl -d $wslDistro -- bash -c "cd $remoteDir && git add -A && git commit -m 'build: full pipeline $stamp' && git push origin main"
        OK "Committed and pushed"
    }
} else { Warn "STAGE 5 skipped." }

Header "ALL DONE  ($(Elapsed))"
Write-Host "  figures/   pipeline outputs"    -ForegroundColor Green
Write-Host "  docs/si/   supplementary info"  -ForegroundColor Green
Write-Host "  main.pdf   manuscript"          -ForegroundColor Green
