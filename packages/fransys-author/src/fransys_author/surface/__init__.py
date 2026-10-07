"""The engineer surface over the author engine (spec ENGINEER-API).

Its names stay off `fransys_author.__all__` until the facade swap (EA-SWAP).
"""

from fransys_author.handles import Terminal

from ._device import Device, TypedDevice, TypedFn
from ._handles import Fn, Pin
from ._layout import Layout
from ._signals import ABOVE, AI, AO, BELOW, CONTROL, DI, DO, EARTHED, GENERIC, IT, SIGNAL
from ._strip import Run, TerminalStrip
from ._units import unit
from .design import Design, design

__all__ = [
    "ABOVE",
    "AI",
    "AO",
    "BELOW",
    "CONTROL",
    "DI",
    "DO",
    "EARTHED",
    "GENERIC",
    "IT",
    "SIGNAL",
    "Design",
    "Device",
    "Fn",
    "Layout",
    "Pin",
    "Run",
    "Terminal",
    "TerminalStrip",
    "TypedDevice",
    "TypedFn",
    "design",
    "unit",
]
