# micrograd — Submission Notes

## Manuscript
- **File:** `manuscript/main.pdf` (31 pages, 0 errors)
- **Cover letter:** `manuscript/cover_letter.pdf`
- **Title:** `micrograd`: An open-source FEniCSx framework for adjoint-based
  topology optimisation of porous microfluidic mixers using
  Brinkman–convection-diffusion equations

## Author
- **Name:** Nisong Monyimba
- **Institution:** University of Ghana, Department of Mathematics
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

## Pre-submission Tasks
- [ ] Register Zenodo DOI at https://zenodo.org
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
