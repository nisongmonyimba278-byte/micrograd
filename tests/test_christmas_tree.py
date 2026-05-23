# tests/test_christmas_tree.py
"""Verify that the Christmas tree density generator works correctly."""
import numpy as np
import pytest
from micrograd.mesh import create_rectangular_mesh
from micrograd.christmas_tree import create_christmas_tree_density
from dolfinx import fem

def test_tree_density_contains_fluid():
    msh, _ = create_rectangular_mesh(2000e-6, 500e-6, 40, 10)
    rho = create_christmas_tree_density(msh, Lx=2000e-6, Ly=500e-6, channel_width=10e-6)
    arr = rho.vector.array
    assert np.any(arr > 0.5), "No fluid nodes found in tree density"
    assert np.any(arr < 0.5), "Density should also contain solid nodes"
    # Check that total fluid area is reasonable (between 5% and 30% of domain)
    area_frac = np.mean(arr)
    assert 0.05 < area_frac < 0.35, f"Fluid area fraction {area_frac} out of expected range"