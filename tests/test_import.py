"""Basic import and API surface tests."""

def test_import_optimizer():
    from micrograd import GradientGeneratorOptimizer
    assert GradientGeneratorOptimizer is not None

def test_import_utilities():
    from micrograd.utilities import (helmholtz_filter, heaviside_projection,
                                      alpha, D_eff)
    assert all(f is not None for f in
               [helmholtz_filter, heaviside_projection, alpha, D_eff])

def test_import_solver():
    from micrograd.solver import forward_solve
    assert forward_solve is not None

def test_import_adjoint():
    from micrograd.adjoint import adjoint_and_sensitivity
    assert adjoint_and_sensitivity is not None

def test_import_optimizer_routines():
    from micrograd.optimizer import (oc_update, nlopt_mma_update,
                                      reset_mma_state, mma_update)
    assert all(f is not None for f in
               [oc_update, nlopt_mma_update, reset_mma_state, mma_update])

def test_import_binary_validation():
    from micrograd.binary_validation import run_binary_validation
    assert run_binary_validation is not None

def test_alpha_floor():
    """alpha() must have a floor even when alpha_min=0."""
    import inspect
    from micrograd.utilities import alpha
    src = inspect.getsource(alpha)
    assert "max_value" in src, "ufl.max_value floor missing from alpha()"
    assert "1e-4" in src, "1e-4 floor value missing from alpha()"

def test_mma_state_reset():
    from micrograd.optimizer import reset_mma_state, _mma_state
    reset_mma_state()
    from micrograd.optimizer import _mma_state as state
    assert state is None, "reset_mma_state() did not clear _mma_state"
