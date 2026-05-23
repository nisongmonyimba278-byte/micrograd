# run_wsl.ps1 — micrograd reproduction pipeline via WSL (fully automatic)
$ErrorActionPreference = "Stop"
$wslDistro     = "Ubuntu"
$condaEnv      = "micrograd-env"
$remoteDir     = "/home/nison/micrograd"
$condaBase     = "/home/nison/miniconda3"
$condaRun      = "$condaBase/bin/conda run -n $condaEnv --no-capture-output"
$windowsSource = "C:\Users\nison\OneDrive\Desktop\micrograd"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  micrograd – WSL reproduction pipeline      " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Check WSL
$wslList = wsl --list --verbose 2>&1 | Out-String
if ($wslList -notmatch "Ubuntu") { Write-Error "Ubuntu not found"; exit 1 }

# 2. Copy project to native Linux filesystem
Write-Host "`n[2] Copying project to Linux filesystem..." -ForegroundColor Yellow
wsl -d $wslDistro -- bash -c "rm -rf $remoteDir; cp -r '/mnt/c/Users/nison/OneDrive/Desktop/micrograd' $remoteDir"

# 3. Ensure conda environment exists and all deps are installed
Write-Host "`n[3] Checking conda environment..." -ForegroundColor Yellow
$envCheck = wsl -d $wslDistro -- bash -c "$condaBase/bin/conda env list 2>&1"
if ($envCheck -notmatch $condaEnv) {
    Write-Host "  Creating environment from environment.yaml..." -ForegroundColor Yellow
    wsl -d $wslDistro -- bash -c "cd $remoteDir && $condaBase/bin/conda env create -f environment.yaml"
    wsl -d $wslDistro -- bash -c "$condaRun pip install "setuptools==59.5.0" nlopt"
} else {
    Write-Host "  Environment found. Ensuring setuptools + nlopt..." -ForegroundColor Green
    wsl -d $wslDistro -- bash -c "$condaRun pip install "setuptools==59.5.0" nlopt 2>/dev/null || true"
}
# Install the micrograd package itself (always, in case source changed)
Write-Host "  Installing micrograd package..." -ForegroundColor Yellow
wsl -d $wslDistro -- bash -c "cd $remoteDir && $condaRun pip install -e . --no-deps"

# 4. Set PYTHONPATH and create output folders
Write-Host "`n[4] Setting PYTHONPATH and output directories..." -ForegroundColor Yellow
wsl -d $wslDistro -- bash -c "mkdir -p $remoteDir/figures $remoteDir/docs/si"
$pyPathLine = "export PYTHONPATH=${remoteDir}:" + '$PYTHONPATH'
wsl -d $wslDistro -- bash -c "grep -qxF '$pyPathLine' ~/.bashrc || echo '$pyPathLine' >> ~/.bashrc"

# 5. Open VSCode via Remote-WSL
Write-Host "`n[5] Opening VSCode in WSL..." -ForegroundColor Yellow
if (Get-Command code -ErrorAction SilentlyContinue) {
    Start-Process "code" -ArgumentList "--remote wsl+$wslDistro $remoteDir"
    Write-Host "  VSCode opened at $remoteDir" -ForegroundColor Green
} else {
    Write-Host "  VSCode not in PATH — skipping. Install from https://code.visualstudio.com" -ForegroundColor Yellow
}

# Helper function (fixed quoting)
function Invoke-WSL([string]$cmd, [string]$label) {
    Write-Host "`n$label" -ForegroundColor Yellow
    # Build the bash command safely, avoiding colon parsing issues
    $bashCmd = "cd $remoteDir && export PYTHONPATH=${remoteDir}:" + '${PYTHONPATH} && ' + "$condaRun $cmd"
    wsl -d $wslDistro -- bash -c $bashCmd
    if ($LASTEXITCODE -ne 0) { Write-Error "FAILED: $label"; exit 1 }
}

# Pipeline
Invoke-WSL "python3 -c 'from micrograd.convergence_study import run_convergence_study; run_convergence_study(lambda x: x[1]/500e-6, mesh_sizes=[(40,10),(80,20),(160,40)], output_dir=\"figures\", max_iter=60)'" "[6] Mesh convergence study"
Invoke-WSL "python3 -c 'from micrograd.filter_sensitivity import run_filter_sensitivity; run_filter_sensitivity(lambda x: x[1]/500e-6, nx=80, ny=20, r_filter_multipliers=[1.0,1.5,2.0,2.5,3.0], output_dir=\"figures\", max_iter=50)'" "[7] Filter sensitivity"
Invoke-WSL "python3 run_stabilization_test.py" "[8] Stabilisation validation"
wsl -d $wslDistro -- bash -c "cd $remoteDir && mv stabilization_outlet.png stabilization_fields.png docs/si/ 2>/dev/null; true"
Invoke-WSL "python3 examples/gallery_targets.py" "[9] Gallery of target profiles"
wsl -d $wslDistro -- bash -c "cd $remoteDir && cp figures/gallery_target_profiles.pdf docs/si/ 2>/dev/null; true"
Invoke-WSL "python3 generate_figures.py" "[10] Main figures"
wsl -d $wslDistro -- bash -c "cd $remoteDir && cp figures/*.pdf figures/*.png docs/si/ 2>/dev/null; true"
Invoke-WSL "python3 generate_si.py" "[11] Supplementary Information"

# MMA (optional — nlopt provides the fallback)
$mmaAvail = wsl -d $wslDistro -- bash -c "$condaRun python3 -c 'import micrograd.compatibility as mc; exit(0 if mc.check_mma_available() else 1)'" 2>$null
if ($LASTEXITCODE -eq 0) {
    Invoke-WSL "python3 run_optimizer_comparison.py" "[12] OC vs MMA"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp docs/si/S4_optimizer_comparison.pdf docs/si/ 2>/dev/null; true"
} else { Write-Host "`n[12] MMA not available — skipping." -ForegroundColor Yellow }

# UQ (optional — requires chaospy)
$uqAvail = wsl -d $wslDistro -- bash -c "$condaRun python3 -c 'import chaospy'" 2>$null
if ($LASTEXITCODE -eq 0) {
    Invoke-WSL "python3 run_uq.py" "[13] UQ"
    wsl -d $wslDistro -- bash -c "cd $remoteDir && cp -r uq/* docs/si/ 2>/dev/null; true"
} else { Write-Host "`n[13] chaospy not installed — skipping UQ." -ForegroundColor Yellow }

Invoke-WSL "python3 run_pareto.py" "[14] Pareto front"
wsl -d $wslDistro -- bash -c "cd $remoteDir && cp -r pareto/* docs/si/ 2>/dev/null; true"

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host "  REPRODUCTION COMPLETE                       " -ForegroundColor Green
Write-Host "    Figures    -> figures/                    " -ForegroundColor Green
Write-Host "    SI package -> docs/si/                    " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
