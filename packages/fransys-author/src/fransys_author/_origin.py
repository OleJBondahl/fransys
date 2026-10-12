"""Where a record was authored: the first call frame outside the skipped packages.

Read once per call; stack introspection of frames already in memory, so not I/O.
"""

import sys
from typing import TYPE_CHECKING

from fransys_model.kernel import Origin

if TYPE_CHECKING:
    from types import FrameType

_SKIPPED = frozenset(
    {"fransys_author", "contextlib"}
)  # contextlib runs a `with d.function(...)` entry


def _hidden(frame: FrameType) -> bool:
    """True when the frame's locals or module globals set a truthy `__tracebackhide__`."""
    return bool(
        frame.f_locals.get("__tracebackhide__", False)
        or frame.f_globals.get("__tracebackhide__", False)
    )


def _skipped(frame: FrameType, packages: frozenset[str]) -> bool:
    module = frame.f_globals.get("__name__", "").partition(".")[0]
    return module in packages or _hidden(frame)


def caller_origin(packages: frozenset[str] = _SKIPPED) -> Origin:
    """The file and line of the first frame outside `packages` that does not hide itself.

    A frame hides itself with pytest's `__tracebackhide__ = True`, as a local or a module global;
    a helper that builds a repeated circuit then reports its caller's line.
    """
    frame = sys._getframe(1)
    while frame is not None and _skipped(frame, packages):
        frame = frame.f_back
    assert frame is not None  # noqa: S101 -- every real call stack bottoms out outside these packages
    return Origin(file=frame.f_code.co_filename, line=frame.f_lineno, note="")
