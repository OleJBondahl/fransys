"""`digest_cached`: one per-digest cache for every derived result of a `Model` (model-0067).

The builders here read nothing but `model.digest`, so a stub with a `digest` stands in for a
`Model`; each builder counts its own calls and returns a fresh object, so identity shows a hit.
"""

import dataclasses
from typing import cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Model, digest_cached


@dataclasses.dataclass(frozen=True)
class _Stub:
    digest: str


def _model(digest: str) -> Model:
    return cast("Model", _Stub(digest))


def _counted(maxsize: int):
    """A cached builder of `maxsize` and the list of digests it was actually built for."""
    built: list[str] = []

    @digest_cached(maxsize)
    def build(model: Model) -> object:
        """Build a fresh object for `model`."""
        built.append(model.digest)
        return object()

    return build, built


def test_an_equal_digest_returns_the_identical_object_and_builds_once() -> None:
    build, built = _counted(2)
    first = build(_model("a"))
    assert build(_model("a")) is first
    assert built == ["a"]
    assert build.builds == 1


def test_a_different_digest_builds_afresh() -> None:
    build, built = _counted(2)
    first = build(_model("a"))
    second = build(_model("b"))
    assert second is not first
    assert built == ["a", "b"]


def test_a_digest_is_evicted_after_maxsize_other_digests() -> None:
    build, built = _counted(2)
    first = build(_model("a"))
    build(_model("b"))
    build(_model("c"))
    again = build(_model("a"))
    assert again is not first
    assert built == ["a", "b", "c", "a"]


def test_maxsize_is_honoured_by_the_decorator_that_was_given_it() -> None:
    """Two results fit in a cache of two; the third digest is what pushes one out."""
    build, built = _counted(2)
    first, second = build(_model("a")), build(_model("b"))
    assert build(_model("a")) is first
    assert build(_model("b")) is second
    assert built == ["a", "b"]


def test_the_least_recently_used_digest_goes_first() -> None:
    build, built = _counted(2)
    kept = build(_model("a"))
    build(_model("b"))
    assert build(_model("a")) is kept
    build(_model("c"))
    assert build(_model("a")) is kept
    assert built == ["a", "b", "c"]


def test_the_shared_size_is_the_default_bound() -> None:
    build, built = _counted(DIGEST_CACHE_SIZE)
    models = [_model(str(n)) for n in range(DIGEST_CACHE_SIZE + 1)]
    for model in models:
        build(model)
    assert build.builds == DIGEST_CACHE_SIZE + 1
    build(models[-1])
    assert build.builds == DIGEST_CACHE_SIZE + 1
    build(models[0])
    assert build.builds == DIGEST_CACHE_SIZE + 2
    assert built[-1] == "0"


def test_cache_clear_forgets_results_and_the_build_count() -> None:
    build, _ = _counted(2)
    first = build(_model("a"))
    build.cache_clear()
    assert build.builds == 0
    assert build(_model("a")) is not first
    assert build.builds == 1


def test_the_builder_keeps_its_name_and_docstring() -> None:
    build, _ = _counted(2)
    assert build.__name__ == "build"
    assert build.__doc__ == "Build a fresh object for `model`."
