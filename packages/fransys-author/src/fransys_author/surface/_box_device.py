"""The device `d.device("E1", None, external=True, pins=(...))` returns: its pins are attributes."""

from typing import TYPE_CHECKING, override

from fransys_author.surface._device import Device

if TYPE_CHECKING:
    from fransys_author.surface._handles import Pin


class BoxDevice(Device):
    """A device with no part: `ext.U` is its pin `U`, as `ext["U"]` is.

    Exists for the type checker only: at run time `Device.__getattr__` and `__dir__` do the work.
    """

    if TYPE_CHECKING:  # the box function stays `ext.box`; every other name is a pin

        @override
        def __getattr__(self, name: str) -> Pin:  # ty: ignore[invalid-method-override] -- a box names pins, not functions
            """The pin named `name`."""
