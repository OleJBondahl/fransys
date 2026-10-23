"""`derive.order.natural_key` is the kernel's key itself: one body for `fr.derive.natural_key`."""

import fransys_kernel
from fransys_model.derive import natural_key, order


def test_derive_natural_key_is_the_kernel_key() -> None:
    """The re-export is the same object, not a copy that could drift."""
    assert order.natural_key is fransys_kernel.natural_key
    assert natural_key is fransys_kernel.natural_key
