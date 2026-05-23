# docs/conf.py
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# Project information
project = 'micrograd'
copyright = '2025, Nisong Monyimba'
author = 'Nisong Monyimba'
version = '1.0.0'
release = '1.0.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',    # generate docs from docstrings
    'sphinx.ext.napoleon',   # support Google/NumPy style docstrings
    'sphinx.ext.viewcode',   # add source code links
]

# Mock imports for the heavy dependencies so that ReadTheDocs can build
# without having FEniCSx installed.
autodoc_mock_imports = [
    'mpi4py',
    'petsc4py',
    'dolfinx',
    'ufl',
    'pyvista',
    'gmsh',
    'meshio',
    'chaospy',
    'nlopt',
]

# Napoleon settings (Google style)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# General configuration
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']