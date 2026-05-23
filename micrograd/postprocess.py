# micrograd/postprocess.py
"""Visualisation and STL export (FEniCSx ≥ 0.9)."""
import numpy as np
import pyvista as pv
from dolfinx import plot

def plot_density(rho_phys, V_rho, filename="density.png"):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib required for plotting.")
    topology, cells, geometry = plot.vtk_mesh(V_rho)
    grid = pv.UnstructuredGrid(cells, geometry, topology)
    grid["density"] = rho_phys.x.array.real
    grid.set_active_scalars("density")
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(grid, show_edges=False, cmap="coolwarm", clim=[0,1])
    plotter.view_xy()
    plotter.show_bounds()
    plotter.screenshot(filename)
    plotter.close()

def export_stl(rho_phys, V_rho, threshold=0.5, filename="channel.stl"):
    topology, cells, geometry = plot.vtk_mesh(V_rho)
    grid = pv.UnstructuredGrid(cells, geometry, topology)
    grid["density"] = rho_phys.x.array.real
    fluid = grid.threshold(value=threshold, scalars="density", preference="cell")
    surface = fluid.extract_surface()
    surface.save(filename)
    print(f"STL exported to {filename}")