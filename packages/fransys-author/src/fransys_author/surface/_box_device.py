"""The device `d.device("E1", None, external=True, pins=(...))` returns: its pins are attributes."""

from typing import Any

from fransys_author.surface._device import Device
from fransys_author.surface._handles import Pin


class BoxDevice(Device[Any, Pin]):
    """A device with no part: `ext.U` is its pin `U`, as `ext["U"]` is; the box function stays `ext.box`.

    Exists for the type checker only: at run time `Device.__getattr__` and `__dir__` do the work.
    """
