# tests/test_mesh_generation.py
"""Test that the rectangular mesh has the expected boundaries."""
import numpy as np
from micrograd.mesh import create_rectangular_mesh

def test_mesh_markers():
    msh, bnd = create_rectangular_mesh(2000e-6, 500e-6, 20, 5)
    # Inlet facets should exist
    assert len(bnd["inlet1"]) > 0
    assert len(bnd["inlet2"]) > 0
    # Outlet should exist
    assert len(bnd["outlet"]) > 0
    # Walls should be present
    assert len(bnd["walls"]) > 0
    # Check that facet_tag contains correct IDs (1, 2, 3)
    assert bnd["facet_tag"].values.min() >= 1
    assert bnd["facet_tag"].values.max() <= 3