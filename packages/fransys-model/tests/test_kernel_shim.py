"""`fransys_model.kernel` re-exports the whole of `fransys_kernel.__all__` (decision 0208)."""

import fransys_kernel
from fransys_model import kernel


def test_the_shim_has_the_kernels_all():
    assert kernel.__all__ == fransys_kernel.__all__
    assert len(kernel.__all__) > 50  # a vacuous empty list would pass the equality


def test_every_shim_name_is_the_kernels_own_object():
    """Aliases, not copies: one registry and one `Record` class per process."""
    for name in fransys_kernel.__all__:
        assert getattr(kernel, name) is getattr(fransys_kernel, name), name
