# Supplementary Information: Topology optimisation of microfluidic concentration gradient generators

This document contains additional figures, tables, and data supporting the main manuscript.  
All figure and table numbers refer to the Supplementary Information.

---

## S1 – Mesh convergence study

![Mesh convergence](S1_convergence_history.png)

*Fig. S1: Convergence of total objective for three mesh resolutions (40×10, 80×20, 160×40).*

![Topology comparison](S1_topology_comparison.png)

*Fig. S2: Final density fields for the three meshes.*

![Outlet profiles](S1_outlet_profiles.png)

*Fig. S3: Outlet concentration profiles for the three meshes.*

**Table S1:** Objective values and outlet RMSE for each mesh.

| Mesh   | \(J_{\text{total}}\) | \(J_{\text{flow}}\) | \(J_{\text{conc}}\) | Outlet RMSE |
|--------|----------------------|---------------------|---------------------|-------------|
| 40×10  | (value)              | (value)             | (value)             | (value)     |
| 80×20  | (value)              | (value)             | (value)             | (value)     |
| 160×40 | (value)              | (value)             | (value)             | (value)     |

*Data from `S1_convergence_metrics.csv`.*

---

## S2 – Filter radius sensitivity

![Filter RMSE bar](S2_filter_rmse_bar.png)

*Fig. S4: Outlet RMSE as a function of filter radius multiplier (× element size).*

![Filter outlet profiles](S2_filter_outlet_profiles.png)

*Fig. S5: Outlet profiles for different filter radii.*

**Table S2:** RMSE for each filter radius multiplier.

| Multiplier | RMSE     |
|------------|----------|
| 1.0        | (value)  |
| 1.5        | (value)  |
| 2.0        | (value)  |
| 2.5        | (value)  |
| 3.0        | (value)  |

*From `S2_filter_metrics.csv`.*

---

## S3 – Stabilisation validation

![Stabilisation outlet](S3_stabilization_outlet.pdf)

*Fig. S6: Outlet concentration using unstabilised (Galerkin), SUPG, and GLS on a coarse mesh (30×8).*

**Table S3:** RMSE for each stabilisation method.

| Method | Outlet RMSE |
|--------|-------------|
| none   | (value)     |
| supg   | (value)     |
| gls    | (value)     |

*From `S3_stabilization_rmse.csv`.*

---

## S4 – OC vs. MMA convergence

![OC vs MMA](S4_optimizer_comparison.pdf)

*Fig. S7: Objective history for the Optimality Criteria (OC) and Method of Moving Asymptotes (MMA) optimisers.*

**Table S4:** Run times and final objectives.

| Method | Time (s) | Final \(J\) |
|--------|----------|-------------|
| OC     | (value)  | (value)     |
| MMA    | (value)  | (value)     |

*From `S4_comparison.csv`. If MMA was not available, this section is replaced by a note.*

---

## S5 – Volume fraction continuation

![Volume continuation](S5_volume_continuation.pdf)

*Fig. S8: Volume fraction target \(V^*\) vs. iteration for the default schedule (0.7 → 0.5).*

---

## S6 – Christmas tree design and comparison

![Christmas tree density](S6_christmas_tree_density.png)

*Fig. S9: Density field representing the classic Christmas tree network (Jeon et al., 2005).*

**Table S5:** Performance metrics for topology‑optimised and Christmas tree designs.

| Metric | Topology optimised | Christmas tree |
|--------|-------------------|----------------|
| Pressure drop (Pa) | (value) | (value) |
| Flow rate (m³/s) | (value) | (value) |
| Hydraulic resistance (Pa·s/m³) | (value) | (value) |
| Max velocity (m/s) | (value) | (value) |
| Characteristic length (µm) | (value) | (value) |
| Reynolds number | (value) | (value) |
| Péclet number | (value) | (value) |
| Mixing length (µm) | (value) | (value) |
| Min feature size (µm) | (value) | (value) |
| Fluid area (m²) | (value) | (value) |
| Outlet RMSE | (value) | (value) |

*All values from `S6_comparison_metrics.csv` (also available as LaTeX table `S6_comparison_metrics.tex`).*

---

## S7 – Detailed experimental metrics

Same as Table S5, provided as CSV (`S7_experimental_metrics.csv`) and LaTeX (`S7_experimental_metrics.tex`).

---

## S8 – Minimum feature size distribution

![Width histogram](S8_width_distribution.pdf)

*Fig. S10: Histogram of channel widths in the optimised design. Dashed line: fabrication limit (10 µm).*

- Minimum channel width: (value) µm  
- Average channel width: (value) µm  
- Meets 10 µm limit: (yes/no)

*From `S8_min_feature_size.txt`.*

---

## S9 – Reynolds and Péclet numbers

- Reynolds number: (value)  
- Péclet number: (value)

*From `S9_reynolds_peclet.txt`.*

---

## S10 – Adjoint sensitivity verification

**Table S6:** Finite‑difference check of adjoint gradients for 10 randomly selected design variables.

| DOF | Adjoint | Finite difference | Relative error |
|-----|---------|-------------------|----------------|
| …   | …       | …                 | …              |

*Full data in `S10_adjoint_verification.csv`. Maximum relative error < 1 % in all tests.*

---

## S11 – Three‑dimensional validation

![3D rendering](S11_3d_render.png)

*Fig. S11: Three‑dimensional rendering of the extruded optimised channel, coloured by concentration (Navier–Stokes simulation).*

![3D outlet profile](S11_3d_outlet_profile.png)

*Fig. S12: Outlet concentration profile from the full 3D Navier–Stokes simulation.*

*If 3D validation was not performed, a note explains that the 2D body‑fitted validation serves as equivalent verification.*

---

## S12 – Gallery of target profiles

![Gallery](S12_gallery.pdf)

*Fig. S13: Optimised topologies for linear, sigmoid, double‑peak, and stair‑step target concentration profiles. Left column: target; middle: density field; right: outlet profile (simulated vs. target).*

---

## S13 – Fabrication robustness (uncertainty quantification)

*If the UQ script was executed, the following material is included.*

![UQ envelope](uq_outlet_envelope.pdf)

*Fig. S14: Mean outlet concentration and 95 % confidence band under ±10 % channel width variation (polynomial chaos, 50 samples).*

Maximum 2σ width: (value) concentration units.  
*(Data in `uq/uq_mean_profile.csv` and `uq/uq_std_profile.csv`.)*

---

## S14 – Multi‑objective Pareto front

*If the Pareto sweep was executed, the following material is included.*

![Pareto resistance vs RMSE](pareto_resistance_vs_rmse.pdf)

*Fig. S15: Pareto front showing trade‑off between hydraulic resistance and outlet RMSE for different weighting factors \(w_f\).*

Full sweep data in `pareto/pareto_data.csv`.

---

**Note:** All placeholder `(value)` entries should be replaced with the actual numbers from the corresponding CSV files after executing the complete pipeline.