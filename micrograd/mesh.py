# micrograd/mesh.py
"""Mesh generation and boundary markers (FEniCSx ≥ 0.9)."""
import numpy as np
import dolfinx
from dolfinx import mesh, fem
from mpi4py import MPI

def create_rectangular_mesh(Lx=2000e-6, Ly=500e-6, nx=80, ny=20):
    """Create a 2D triangular mesh of a rectangle and return mesh, boundary markers."""
    comm = MPI.COMM_SELF
    msh = mesh.create_rectangle(comm, [[0.0, 0.0], [Lx, Ly]], [nx, ny],
                                cell_type=dolfinx.mesh.CellType.triangle)
    tdim = msh.topology.dim
    fdim = tdim - 1

    def left(x): return np.isclose(x[0], 0.0)
    def right(x): return np.isclose(x[0], Lx)
    def top(x): return np.isclose(x[1], Ly)
    def bottom(x): return np.isclose(x[1], 0.0)

    left_facets = mesh.locate_entities_boundary(msh, fdim, left)
    right_facets = mesh.locate_entities_boundary(msh, fdim, right)
    top_facets = mesh.locate_entities_boundary(msh, fdim, top)
    bottom_facets = mesh.locate_entities_boundary(msh, fdim, bottom)

    left_midpoints = mesh.compute_midpoints(msh, fdim, left_facets)
    y_left = left_midpoints[:, 1]
    inlet1_facets = left_facets[y_left > Ly/2]
    inlet2_facets = left_facets[y_left <= Ly/2]

    wall_facets = np.hstack([top_facets, bottom_facets])
    facet_indices = np.hstack([inlet1_facets, inlet2_facets, right_facets, wall_facets])
    facet_markers = np.hstack([
        1 * np.ones(len(inlet1_facets), dtype=np.int32),
        2 * np.ones(len(inlet2_facets), dtype=np.int32),
        3 * np.ones(len(right_facets), dtype=np.int32),
        4 * np.ones(len(wall_facets), dtype=np.int32)
    ])
    sorted_idx = np.argsort(facet_indices)
    facet_tag = mesh.meshtags(msh, fdim, facet_indices[sorted_idx], facet_markers[sorted_idx])

    boundary_data = {
        "inlet1": inlet1_facets,
        "inlet2": inlet2_facets,
        "outlet": right_facets,
        "walls": np.hstack([top_facets, bottom_facets]),
        "facet_tag": facet_tag,
        "Lx": Lx,
        "Ly": Ly,
    }
    return msh, boundary_data