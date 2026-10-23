"""The drawn-pages memo keeps every build's drawings for the worker's life (DRAWN-MEMO).

A module-cached builder builds once per xdist worker; later tests of the module read its
drawings after any number of other builds. A count eviction made that read a LookupError.
"""

from types import SimpleNamespace
from typing import Any, cast

import _drawn_pages
import pytest


def _model(digest: str) -> Any:  # a stand-in with the one field the memo reads
    return cast("Any", SimpleNamespace(digest=digest))


def test_the_first_build_is_still_noted_after_many_later_builds():
    def fake_build(digest):
        return SimpleNamespace(model=SimpleNamespace(digest=digest), drawings={digest: digest})

    noting = _drawn_pages._noting(fake_build)
    digests = [f"drawn-memo-{n}" for n in range(200)]
    for digest in digests:
        noting(digest)
    try:
        for digest in digests:
            assert _drawn_pages.drawn_pages(_model(digest)) == {digest: digest}
    finally:
        for digest in digests:
            _drawn_pages._NOTED.pop(digest, None)


def test_an_unbuilt_model_is_still_a_lookup_error():
    with pytest.raises(LookupError):
        _drawn_pages.drawn_pages(_model("drawn-memo-never-built"))
