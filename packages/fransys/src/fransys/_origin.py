"""Where a record was authored: the first call frame outside this package.

Stack introspection of frames already in memory, not I/O: free per public call, no extra cost.
"""

import sys

from fransys_model.kernel import Origin

_PACKAGE = "fransys"


def caller_origin() -> Origin:
    """The file and line of the first frame whose module is not `fransys` itself.

    Compares module names (`f_globals["__name__"]`), not paths: this package's frames are skipped,
    the consumer's script or test is captured.
    """
    frame = sys._getframe(1)  # noqa: SLF001 -- Origin needs the caller's frame; CPython's documented call
    while frame is not None and frame.f_globals.get("__name__", "").partition(".")[0] == _PACKAGE:
        frame = frame.f_back
    assert frame is not None  # noqa: S101 -- every real call stack bottoms out outside this package
    return Origin(file=frame.f_code.co_filename, line=frame.f_lineno, note="")
