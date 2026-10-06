"""Where a record was authored: the first call frame outside this package (spec A10).

Read once per call; stack introspection of frames already in memory, so not I/O.
"""

import sys

from fransys_model.kernel import Origin

_PACKAGE = "fransys_author"


def caller_origin() -> Origin:
    """The file and line of the first frame outside `fransys_author`, by module (spec A10)."""
    frame = sys._getframe(1)
    while frame is not None and frame.f_globals.get("__name__", "").partition(".")[0] == _PACKAGE:
        frame = frame.f_back
    assert frame is not None  # noqa: S101 -- every real call stack bottoms out outside this package
    return Origin(file=frame.f_code.co_filename, line=frame.f_lineno, note="")
