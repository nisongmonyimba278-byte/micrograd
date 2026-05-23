# tests/test_mma_fallback.py
"""Test that MMA fallback to OC works gracefully."""
import warnings
import pytest
from micrograd.compatibility import fallback_to_oc

def test_fallback_to_oc():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        method = fallback_to_oc('mma')
        # If MMA is not installed, a warning should have been issued and method returns 'oc'
        if not method == 'oc':
            # If MMA is installed, the warning wasn't raised and method stays 'mma'
            assert method == 'mma'
        else:
            # Fallback occurred; a warning should have been issued
            assert len(w) == 1
            assert "Falling back to Optimality Criteria" in str(w[0].message)