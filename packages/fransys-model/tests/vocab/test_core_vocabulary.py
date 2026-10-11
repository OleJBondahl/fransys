"""The core vocabulary as a whole.

Every case here is about what the kinds do together: their fields against the DESIGN table,
their enums resolving at runtime, their normalisation surviving alias rewriting and loading,
and one model holding a record of each kind.
"""

import sys
from typing import TYPE_CHECKING, Any
lazy from enum import Enum

import pytest

from fransys_model.kernel import (
    Id,
    Origin,
    SchemaError,
    make_id,
)
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.project import Project
from fransys_model.vocab.templates import (
    FunctionTemplate,
    InternalLink,
    Part,
    PartLibrary,
    PortTemplate,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

_ORIGIN = Origin(file="test_core_vocabulary.py", line=1, note="")

# Field by field, without the `id`, `key` and `ext` every record has.
_DESIGNED: dict[type, tuple[str, ...]] = {
    PartLibrary: ("name", "version"),
    Part: ("mpn", "manufacturer", "description", "category", "class_code", "library"),
    FunctionTemplate: ("part", "name", "kind", "protection_type", "energy"),
    PortTemplate: ("function", "name", "role", "marking", "pole_side", "conductor_mark", "joins"),
    InternalLink: ("a", "b", "kind", "rest"),
    Item: (
        "part",
        "parent",
        "position",
        "tag",
        "description",
        "installed",
        "unit",
        "external",
    ),
    Function: ("item", "template", "name", "kind"),
    Port: ("function", "template", "name", "role", "marking"),
    Net: ("name", "net_class", "ports", "potential"),
    Conductor: ("a", "b", "kind", "carrier"),
    Mate: ("a", "b"),
    AspectNode: ("aspect", "parent", "label", "description"),
    Placement: ("item", "node"),
    Project: ("title", "number", "customer", "revision", "author", "notice", "version"),
}

# Every reference in the vocabulary: (kind, field) -> the kind it names.
_REFERENCES = {
    ("part", "library"): "part_library",
    ("function_template", "part"): "part",
    ("port_template", "function"): "function_template",
    ("port_template", "joins"): "port_template",
    ("internal_link", "a"): "port_template",
    ("internal_link", "b"): "port_template",
    ("item", "part"): "part",
    ("item", "parent"): "item",
    ("item", "unit"): "unit",
    ("function", "item"): "item",
    ("function", "template"): "function_template",
    ("port", "function"): "function",
    ("port", "template"): "port_template",
    ("net", "ports"): "port",
    ("conductor", "a"): "port",
    ("conductor", "b"): "port",
    ("conductor", "carrier"): "item",
    ("mate", "a"): "function",
    ("mate", "b"): "function",
    ("aspect_node", "parent"): "aspect_node",
    ("placement", "item"): "item",
    ("placement", "node"): "aspect_node",
}

# Field -> the enum it is annotated with.
_ENUM_FIELDS: dict[tuple[type, str], type[Enum]] = {
    (Part, "category"): PartCategory,
    (FunctionTemplate, "kind"): FunctionKind,
    (PortTemplate, "role"): PortRole,
    (InternalLink, "kind"): LinkKind,
    (Function, "kind"): FunctionKind,
    (Port, "role"): PortRole,
    (Net, "net_class"): NetClass,
    (Conductor, "kind"): ConductorKind,
    (AspectNode, "aspect"): Aspect,
}


def _key_id(cls: type, *key: str) -> Id[Any]:
    return make_id(cls, key)


def _fransys_modules() -> list[str]:
    prefix = "fransys_model."
    return [name for name in sys.modules if name == "fransys_model" or name.startswith(prefix)]


@pytest.fixture
def fresh_package() -> Iterator[None]:
    """Import the package again from nothing, so its registries start empty; then restore it."""
    saved = {name: sys.modules[name] for name in _fransys_modules()}
    for name in saved:
        del sys.modules[name]
    try:
        yield
    finally:
        for name in _fransys_modules():
            del sys.modules[name]
        sys.modules.update(saved)


def _conductor(a: Any, b: Any) -> Conductor:
    return Conductor(
        id=_key_id(Conductor, "c"),
        key=("c",),
        a=a,
        b=b,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def test_a_conductor_refuses_the_same_port_at_both_ends() -> None:
    """Exactly two ends means two different ports."""
    port = _key_id(Port, "a")
    with pytest.raises(SchemaError, match="two different ports") as excinfo:
        _conductor(port, port)
    assert excinfo.value.record_id == _key_id(Conductor, "c")
