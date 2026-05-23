# setup.py
from setuptools import setup, find_packages

setup(
    name="micrograd",
    version="1.0.0",
    description="Topology optimisation of microfluidic gradient generators for arbitrary outlet profiles",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Nisong Monyimba",
    author_email="nmonyimb@asu.edu",
    url="https://github.com/yourusername/micrograd",  # replace with your actual username
    packages=find_packages(),
    install_requires=[
        "numpy>=1.23.2",        # <-- pinned to the Docker image's native version
        "scipy>=1.11.4",
        "matplotlib>=3.8.3",
        "pyvista>=0.43.3",
        "meshio>=5.3.4",
    ],
    extras_require={
        "fenics": [
            "fenics-dolfinx>=0.6.0",
            "petsc4py>=3.19.2",
            "mpi4py>=3.1.5",
        ],
        "all": [
            "chaospy>=4.3.11",
            "gcma>=1.0.3",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    python_requires=">=3.9",
)