# micrograd/compatibility.py
"""
Graceful fallback for optional dependencies.
Usage:
    from .compatibility import check_mma_available, fallback_to_oc
"""

import warnings

def check_mma_available():
    """Return True if a working MMA implementation is available (gcma or nlopt)."""
    try:
        import gcma
        return True
    except ImportError:
        pass
    try:
        import nlopt
        # Check that LD_MMA algorithm exists
        try:
            nlopt.algorithm_name(nlopt.LD_MMA)
            return True
        except:
            pass
    except ImportError:
        pass
    return False

def fallback_to_oc(method):
    """If method is 'mma' but MMA unavailable, issue warning and return 'oc'."""
    if method == 'mma' and not check_mma_available():
        warnings.warn(
            "MMA optimizer requested but neither 'gcma' nor 'nlopt' found. "
            "Falling back to Optimality Criteria (OC). Install 'gcma' via: pip install gcma",
            RuntimeWarning
        )
        return 'oc'
    return method

def check_pyvista():
    """PyVista is optional for 3D plots."""
    try:
        import pyvista
        return True
    except ImportError:
        warnings.warn("PyVista not installed – 3D rendering disabled.")
        return False