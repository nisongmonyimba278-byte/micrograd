# micrograd/uncertainty_quantification.py
"""
Uncertainty quantification for fabrication tolerances using polynomial chaos expansion.
Assesses the effect of channel width variations on the outlet concentration profile.
"""
import numpy as np
import chaospy as cp
import matplotlib.pyplot as plt
import os
from dolfinx import fem
from .solver import forward_solve


def evaluate_outlet_profile(msh, boundary_data, rho_phys, target_expr):
    """
    Solve forward problem and return the outlet concentration profile.
    
    Args:
        msh: DOLFINx mesh.
        boundary_data: dict with facet markers.
        rho_phys: Physical density field (fem.Function).
        target_expr: callable target function (unused here, included for consistency).
        
    Returns:
        y_out (numpy array): y‑coordinates on outlet, sorted.
        c_out (numpy array): concentration values at those points.
        c_h (fem.Function): the full concentration field.
    """
    u_h, p_h, c_h = forward_solve(msh, boundary_data, rho_phys)
    V_conc = c_h.function_space
    outlet_facets = boundary_data["outlet"]
    fdim = msh.topology.dim - 1
    dofs = fem.locate_dofs_topological(V_conc, fdim, outlet_facets)
    x = V_conc.tabulate_dof_coordinates()[dofs]
    y_out = x[:, 1]
    c_out = c_h.x.array[dofs]
    idx = np.argsort(y_out)
    return y_out[idx], c_out[idx], c_h


def perturb_density_morph(msh, rho_base, width_variation, threshold=0.5):
    """
    Simulate channel width variation by shifting the density field.
    
    A positive width_variation (e.g. +0.1) widens channels (adds material),
    a negative variation narrows them. The density is offset by a scaled
    value and then clamped to [0, 1].
    
    Args:
        msh: DOLFINx mesh (unused, kept for interface uniformity).
        rho_base: baseline physical density (fem.Function).
        width_variation: relative change (e.g. -0.1 to 0.1).
        threshold: nominal threshold (not used directly).
        
    Returns:
        rho_pert: new density function.
    """
    delta_rho = width_variation * 0.1   # heuristic scaling
    rho_pert = fem.Function(rho_base.function_space)
    rho_pert.x.array[:] = np.clip(rho_base.x.array + delta_rho, 0.0, 1.0)
    return rho_pert


def run_chaospy_uq(optimizer, target_expr, num_samples=50,
                   variation_range=(-0.1, 0.1), output_dir="uq"):
    """
    Perform polynomial chaos expansion (PCE) based UQ on the optimized design.
    
    Assumes a single random variable (uniform) representing channel width variation.
    Fits a PCE of order 3 using least‑squares regression on Latin Hypercube samples.
    Plots the mean outlet profile ± 2σ envelope and saves summary statistics.
    
    Args:
        optimizer: a trained GradientGeneratorOptimizer instance (must contain
                   .msh, .boundary_data, .rho_phys).
        target_expr: target concentration function (callable).
        num_samples: number of forward solves for PCE regression.
        variation_range: tuple (min, max) for the uniform width variation.
        output_dir: directory to save figures and CSV files.
        
    Returns:
        dict with keys: y_common, mean, std, samples.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Extract baseline
    msh = optimizer.msh
    bnd = optimizer.boundary_data
    rho_baseline = optimizer.rho_phys

    # Common output grid (y‑coordinates)
    y_common = np.linspace(0.0, bnd["Ly"], 50)
    num_y = len(y_common)

    # Define random variable (uniform distribution)
    xi = cp.Uniform(variation_range[0], variation_range[1])
    distribution = cp.J(xi)

    # Generate collocation samples
    samples = distribution.sample(num_samples, rule="latin_hypercube")
    # samples shape: (1, num_samples)

    # Evaluate forward model at each sample
    all_profiles = np.zeros((num_samples, num_y))
    print(f"Running UQ with {num_samples} samples...")
    for i in range(num_samples):
        var = samples[0, i]
        # Perturb density
        rho_pert = perturb_density_morph(msh, rho_baseline, var)
        # Solve forward problem
        y_out, c_out, _ = evaluate_outlet_profile(msh, bnd, rho_pert, target_expr)
        # Interpolate to common grid
        all_profiles[i, :] = np.interp(y_common, y_out, c_out)

    # Build PCE (order 3)
    polynomial_order = 3
    expansion = cp.generate_expansion(polynomial_order, distribution)

    # Fit PCE and compute statistics at each y location
    mean_profile = np.zeros(num_y)
    std_profile = np.zeros(num_y)
    for j in range(num_y):
        approx = cp.fit_regression(expansion, samples, all_profiles[:, j])
        mean_profile[j] = cp.E(approx, distribution)
        std_profile[j] = cp.Std(approx, distribution)

    # Plot mean ± 2*std envelope
    plt.figure(figsize=(7, 5))
    plt.fill_between(y_common * 1e6,
                     mean_profile - 2 * std_profile,
                     mean_profile + 2 * std_profile,
                     alpha=0.3, color='blue', label='95% confidence')
    plt.plot(y_common * 1e6, mean_profile, 'b-', label='Mean profile')
    target_vals = target_expr(np.array([np.zeros_like(y_common), y_common]))
    plt.plot(y_common * 1e6, target_vals, 'k--', label='Target')
    plt.xlabel('y (µm)')
    plt.ylabel('Concentration')
    plt.legend()
    plt.title('Uncertainty Quantification of Outlet Profile')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "uq_outlet_envelope.pdf"))
    plt.close()

    # Save summary statistics as CSV
    np.savetxt(os.path.join(output_dir, "uq_mean_profile.csv"),
               np.column_stack((y_common * 1e6, mean_profile)),
               header="y_um,concentration_mean", delimiter=",")
    np.savetxt(os.path.join(output_dir, "uq_std_profile.csv"),
               np.column_stack((y_common * 1e6, std_profile)),
               header="y_um,concentration_std", delimiter=",")

    print(f"UQ completed. Mean outlet profile and 95% envelope saved in {output_dir}")
    return {
        "y_common": y_common,
        "mean": mean_profile,
        "std": std_profile,
        "samples": all_profiles
    }