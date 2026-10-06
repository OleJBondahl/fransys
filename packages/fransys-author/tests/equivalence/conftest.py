"""The equivalence helper (EA12): two scripts, one model digest, and the first differing records."""

from collections.abc import Callable
from itertools import islice

import pytest

from fransys_model.kernel import Draft, Origin, Record, freeze, make_id, merge
from fransys_model.vocab import (
    FunctionKind,
    FunctionTemplate,
    Part,
    PartCategory,
    PartLibrary,
    PortRole,
    PortTemplate,
)

Script = Callable[[Draft], Draft]
_SHOWN = 8


def _by_key(draft: Draft) -> dict[tuple[str, tuple[str, ...]], Record]:
    return {(type(r).__name__, r.key): r for r in draft.records()}


def first_differences(a: Draft, b: Draft) -> list[str]:
    """Up to a few lines naming records only in `a`, only in `b`, or changed between them."""
    ra, rb = _by_key(a), _by_key(b)
    lines = [f"only in A: {k[0]} {'/'.join(k[1])}" for k in ra if k not in rb]
    lines += [f"only in B: {k[0]} {'/'.join(k[1])}" for k in rb if k not in ra]
    lines += [
        f"changed: {k[0]} {'/'.join(k[1])}\n  A {ra[k]!r}\n  B {rb[k]!r}"
        for k in ra
        if k in rb and ra[k] != rb[k]
    ]
    return list(islice(lines, _SHOWN))


def assert_same_model(library: Draft, first: Script, *others: Script) -> str:
    """Build each script over `library`, freeze, and assert one model digest; return it."""
    base = first(library)
    digest = freeze(merge(library, base)).digest
    for number, script in enumerate(others, start=2):
        draft = script(library)
        other = freeze(merge(library, draft)).digest
        if other != digest:
            shown = "\n".join(first_differences(base, draft))
            pytest.fail(f"script {number} builds another model than script 1:\n{shown}")
    return digest


@pytest.fixture
def same_model() -> Callable[..., str]:
    """`assert_same_model` as a fixture, for tests that cannot import this conftest."""
    return assert_same_model


@pytest.fixture
def library(parts: Draft) -> Draft:
    """The author tests' parts plus `TEST-SENSOR`: one `sensor` function with `+`, `-` and `OUT`."""
    origin = Origin(file="<equivalence fixture>", line=1, note="sensor part")
    lib_key = ("part_library", "test-sensors")
    lib = PartLibrary(
        id=make_id(PartLibrary, lib_key), key=lib_key, name="test-sensors", version="1"
    )
    key = ("part", "TestCo", "TEST-SENSOR")
    part = Part(
        id=make_id(Part, key),
        key=key,
        mpn="TEST-SENSOR",
        manufacturer="TestCo",
        description="test sensor",
        category=PartCategory.GENERIC,
        class_code="B",
        library=lib.id,
    )
    fkey = (*key, "function", "sensor")
    function = FunctionTemplate(
        id=make_id(FunctionTemplate, fkey),
        key=fkey,
        part=part.id,
        name="sensor",
        kind=FunctionKind.SENSOR,
    )
    parts.extend((lib, part, function), origin=origin)
    for name in ("+", "-", "OUT"):
        pkey = (*fkey, "port", name)
        port = PortTemplate(
            id=make_id(PortTemplate, pkey),
            key=pkey,
            function=function.id,
            name=name,
            role=PortRole.GENERIC,
        )
        parts.add(port, origin=origin)
    return parts
