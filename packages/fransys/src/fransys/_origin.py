"""Where a record was authored: the first call frame outside this package.

Stack introspection of frames already in memory, not I/O: free per public call, no extra cost.
"""

from typing import TYPE_CHECKING

from fransys_author import caller_origin as _caller_origin

if TYPE_CHECKING:
    from fransys_model.kernel import Origin

_PACKAGES = frozenset({"fransys"})


def caller_origin() -> Origin:
    """The file and line of the first frame whose module is not `fransys` itself.

    This wrapper's own frame is `fransys`, so the shared walk starts past it; a frame that sets
    `__tracebackhide__` is skipped too.
    """
    return _caller_origin(_PACKAGES)
