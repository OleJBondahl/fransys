"""The line of a caller's own call, for the origin tests' `+ 1` arithmetic."""

import inspect


def here() -> int:
    """The line number of the caller's own call to this helper."""
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    return int(frame.f_back.f_lineno)
