"""The equivalence fixtures; the helpers are in `equivalence_helpers`."""

lazy from collections.abc import Callable

import pytest
from equivalence_helpers import assert_same_model

from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab import (
    FunctionKind,
    FunctionTemplate,
    Part,
    PartCategory,
    PartLibrary,
    PortBoundary,
    PortTemplate,
)


@pytest.fixture
def same_model() -> Callable[..., str]:
    """`assert_same_model` as a fixture, for tests that cannot import this conftest."""
    return assert_same_model


@pytest.fixture
def library(parts: Draft) -> Draft:
    """The author tests' parts plus `TEST-SENSOR`: one `sensor` function with `+`, `-` and `OUT`."""
    origin = Origin(file="<equivalence fixture>", line=1, note="sensor part")
    lib_key = ("part_library", "test-sensors")
    lib = PartLibrary(id=make_id(PartLibrary, lib_key), key=lib_key, name="test-sensors", version="1")
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
            boundary=PortBoundary.GENERIC,
        )
        parts.add(port, origin=origin)
    return parts
