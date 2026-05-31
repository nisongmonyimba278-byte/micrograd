# micrograd — Submission Notes

## Manuscript
- **File:** `manuscript/main.pdf` (31 pages, 0 errors)
- **Cover letter:** `manuscript/cover_letter.pdf`
- **Title:** `micrograd`: An open-source FEniCSx framework for adjoint-based
  topology optimisation of porous microfluidic mixers using
  Brinkman–convection-diffusion equations

## Author
- **Name:** Nisong Monyimba
- **Institution:** School of Biological and Health Systems Engineering, Arizona State University
- **Email:** nisongmonyimba278@gmail.com

## Key Results
| Result | Value |
|--------|-------|
| Primary RMSE (linear, 1400 iter) | 0.058 |
| Short-run RMSE (600 iter) | 0.079 |
| Gray fraction (β=128) | 0.074 |
| Binary gap | +356% |
| 160×40 RMSE (600 iter) | 0.091 |
| 160×40 RMSE (2400 iter) | 0.107 |
| OC scaling insensitivity | 0.01× to 10000× — identical convergence |

## Four Novelties
1. Continuous adjoint for coupled Brinkman–convection-diffusion
2. SUPG-stabilised adjoint at Pe~1e2–1e5
3. Modular continuation schedule (5 components, each with diagnosed failure mode)
4. End-to-end reproducibility (1 hr laptop, Docker, CI, Zenodo)

## Submission Targets
1. **PRIMARY:** Engineering with Computers (Springer) — 8/10
   - https://www.springer.com/journal/366
2. **FALLBACK:** Computers & Fluids (Elsevier) — 7.5/10
3. **PREPRINT:** arXiv cs.NA (cross-list: physics.flu-dyn) — BEFORE journal

## Pre-submission Tasks (REQUIRED — EwC will reject without these)

### ITEM 1: Register Zenodo DOI (5 minutes, free, REQUIRED)
```bash
cd ~/micrograd
git archive --format=zip HEAD -o micrograd_v1.0.zip
# Go to https://zenodo.org → New upload
# Upload micrograd_v1.0.zip
# Title: micrograd: FEniCSx topology optimisation of Brinkman-convection-diffusion systems
# Authors: Nisong Monyimba (Arizona State University)
# License: MIT
# Click 'Reserve DOI' BEFORE publishing
# Copy the DOI (format: 10.5281/zenodo.XXXXXXX)
bash submission_checklist.sh --set-doi 10.5281/zenodo.XXXXXXX
```

### ITEM 2: Professional GitHub URL (10 minutes)
EwC reviewers may question a username with numbers (nisongmonyimba278-byte).
Options (choose one):
- Create a GitHub org: github.com/micrograd-fenicsx/micrograd
- Rename your GitHub account to your real name
- Transfer the repo to a university org if available
After moving:
```bash
# Update the URL in manuscript
find manuscript -name '*.tex' -exec sed -i \
  's|nisongmonyimba278-byte/micrograd|YOUR-NEW-ORG/micrograd|g' {} \;
bash submission_checklist.sh --recompile
git add -A && git commit -m 'update: professional GitHub URL'
git push origin main
```

### ITEM 3: ORCID and real affiliation
Add to main.tex author block:
```latex
\author{Nisong Monyimba\textsuperscript{1}\thanks{ORCID: 0009-0000-7558-8580}}
\affil{\textsuperscript{1}School of Biological and Health Systems Engineering,
       Arizona State University, Tempe, AZ, USA}
```
Register free ORCID at https://orcid.org if you do not have one.

### ITEM 4: $(pwd) → ${PWD} portability ✅ DONE
Already fixed in all .tex and .sh files.

- [ ] Register Zenodo DOI (Item 1 above)
- [ ] Fix GitHub URL (Item 2 above)
- [ ] Add ORCID to main.tex (Item 3 above)
- [x] Fix $(pwd) → ${PWD} (Item 4 — done)
- [ ] Upload preprint to arXiv (cs.NA)
- [ ] Submit to Engineering with Computers

## Commands
```bash
bash submission_checklist.sh                          # show checklist
bash submission_checklist.sh --set-doi 10.5281/zenodo.1234567
bash submission_checklist.sh --arxiv-prep             # make tarball
bash submission_checklist.sh --arxiv-done             # mark submitted
bash submission_checklist.sh --ewc-done               # mark submitted
bash submission_checklist.sh --recompile              # recompile PDF
```

## Suggested Reviewers (in cover letter)
| Name | Institution | Expertise |
|------|------------|-----------|
| Prof. Ole Sigmund | DTU | Topology optimisation |
| Prof. Boyan Lazarov | DTU/LLNL | Helmholtz filtering, FEniCS |
| Dr. Florian Wechsung | NYU | FEniCSx adjoint methods |
| Prof. Kurt Maute | CU Boulder | TO, adjoint methods |
