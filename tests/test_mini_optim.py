# tests/test_mini_optim.py
"""Mini optimisation that runs on a tiny mesh for CI."""
import numpy as np
from micrograd import GradientGeneratorOptimizer

def linear_target(x):
    return x[1] / 500e-6

def test_mini_optimisation():
    opt = GradientGeneratorOptimizer(Lx=2000e-6, Ly=500e-6, nx=20, ny=5,
                                     target_expr=linear_target, V_star=0.5)
    # Use only 10 iterations and a single beta value
    rho_phys = opt.run(max_iter=10,
                       beta_continuation=[1],   # no sharpening
                       V_star_schedule=[(0, 0.5)],  # constant volume fraction
                       method='oc')
    # Check that the optimizer produced a density field with some variation
    arr = rho_phys.vector.array
    assert arr.min() < 0.8, "Density should have some solid regions"
    assert arr.max() > 0.2, "Density should have some fluid regions"
    # Check that objective improved
    initial_J = opt.history[0, 2]
    final_J = opt.history[-1, 2]
    assert final_J < initial_J, "Optimisation should reduce total objective"