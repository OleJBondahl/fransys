"""WP8 tests: the core vocabulary as a whole (ROADMAP WP8, design/vocabulary.md 6).

Every case here is about what the kinds do together: their fields against the DESIGN table,
their enums resolving at runtime, their normalisation surviving alias rewriting and loading,
and one model holding a record of each kind.
"""

import dataclasses
import importlib
import inspect
import json
import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

import pytest
from examples import core_model

from fransys_model import vocab
from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    Origin,
    SchemaError,
    check_value,
    dumps,
    field_specs,
    freeze,
    loads,
    make_id,
)
from fransys_model.kernel.registry import namespace_of, registered_namespaces
from fransys_model.kernel.schema import annotations_of
from fransys_model.vocab import enums
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
from fransys_model.vocab.tables import nets
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

# design/vocabulary.md 6, field by field, without the `id`, `key` and `ext` every record has.
_DESIGNED: dict[type, tuple[str, ...]] = {
    PartLibrary: ("name", "version"),
    Part: ("mpn", "manufacturer", "description", "category", "class_code", "library"),
    FunctionTemplate: ("part", "name", "kind", "protection_type", "energy"),
    PortTemplate: ("function", "name", "role", "marking", "pole_side", "conductor_mark"),
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

# Every reference in design/vocabulary.md 6: (kind, field) -> the kind it names.
_REFERENCES = {
    ("part", "library"): "part_library",
    ("function_template", "part"): "part",
    ("port_template", "function"): "function_template",
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


@pytest.mark.usefixtures("fresh_package")
def test_importing_vocab_registers_the_namespaces_after_core_in_the_designed_order() -> None:
    """The kernel alone knows `core`; `vocab` names `facet` and `layout` (decision 0009)."""
    registry = importlib.import_module("fransys_model.kernel.registry")
    assert registry.registered_namespaces() == ("core",)
    importlib.import_module("fransys_model.vocab")
    assert registry.registered_namespaces() == ("core", "facet", "layout")


def test_a_kinds_namespace_is_its_prefix() -> None:
    """`item` is `core`, `facet.terminal` is `facet`, `layout.page` is `layout`."""
    assert registered_namespaces() == ("core", "facet", "layout")
    assert namespace_of("item") == "core"
    assert namespace_of("facet.terminal") == "facet"
    assert namespace_of("layout.page") == "layout"


@pytest.mark.parametrize("cls", list(_DESIGNED), ids=lambda cls: cls.__name__)
def test_every_core_kind_has_exactly_the_designed_fields(cls: type) -> None:
    """The field list is design/vocabulary.md 6's, plus the `id`, `key` and `ext` every record
    has."""
    names = {spec.name for spec in field_specs(cls)}
    assert names == {"id", "key", "ext", *_DESIGNED[cls]}


def test_every_reference_names_the_kind_designed() -> None:
    """`field_specs` resolves every forward name, and no other field is a reference."""
    found = {
        (vars(cls)["__kind__"], spec.name): spec.ref_kind
        for cls in _DESIGNED
        for spec in field_specs(cls)
        if spec.ref_kind is not None
    }
    assert found == _REFERENCES


@pytest.mark.parametrize(("cls", "name"), list(_ENUM_FIELDS), ids=str)
def test_an_enum_field_resolves_to_its_enum_at_runtime(cls: type, name: str) -> None:
    """An enum imported only for type checking would leave the field with no shape (5.3)."""
    assert annotations_of(cls)[name] is _ENUM_FIELDS[(cls, name)]


def test_every_vocabulary_enum_is_registered_and_holds_only_strings() -> None:
    """`register_enum` is what admits a member as a `Value`, and members are written by value."""
    classes = [
        member
        for _, member in inspect.getmembers(enums, inspect.isclass)
        if issubclass(member, Enum) and member.__module__ == enums.__name__
    ]
    assert len(classes) == 19
    for cls in classes:
        for member in cls:
            check_value(member)
            assert type(member.value) is str


def test_a_field_with_a_wrong_enum_is_a_schema_error_at_freeze() -> None:
    """The per-field check needs the enum resolved, which is the point of importing it."""
    draft = Draft()
    other: Any = PortRole.PE
    draft.add(
        Function(
            id=_key_id(Function, "f"),
            key=("f",),
            item=_key_id(Item, "i"),
            template=None,
            name="f",
            kind=other,
        ),
        origin=_ORIGIN,
    )
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    assert any(
        isinstance(error, SchemaError) and "kind" in str(error) for error in excinfo.value.errors
    )


def test_a_model_of_every_core_kind_freezes_and_round_trips() -> None:
    """Enums, optional ids, tuples of ids and the `Decimal`-free strings all come back equal."""
    model = core_model()
    assert len(model.tables) == len(_DESIGNED)
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.digest == model.digest
    assert '"electromechanical"' in dumps(model)


def test_a_net_keeps_its_ports_in_id_order_whatever_order_they_were_given() -> None:
    """`Net.ports` is a set: two orders are one record, and `dumps` writes it sorted."""
    model = core_model()
    written_backwards = tuple(reversed(sorted(next(iter(nets(model).values())).ports)))
    assert written_backwards != tuple(sorted(written_backwards))
    net = next(iter(nets(model).values()))
    assert net.ports == tuple(sorted(net.ports))
    assert dumps(loads(dumps(model))) == dumps(model)


def _net(ports: Any) -> Net:
    return Net(id=_key_id(Net, "n"), key=("n",), name=None, net_class=NetClass.GENERIC, ports=ports)


def test_two_nets_listing_the_same_ports_in_different_orders_are_equal() -> None:
    """The order was never a fact: the records compare and hash alike."""
    low, high = _key_id(Port, "a"), _key_id(Port, "b")
    assert _net((high, low)) == _net((low, high))
    assert _net((high, low)).ports == tuple(sorted((low, high)))


def test_a_net_refuses_a_port_listed_twice() -> None:
    """`ports` is a set; a repeat is a mistake to say, not a duplicate to drop quietly."""
    port = _key_id(Port, "a")
    with pytest.raises(SchemaError, match="twice") as excinfo:
        _net((port, port))
    assert excinfo.value.record_id == _key_id(Net, "n")


@pytest.mark.parametrize(
    "ports",
    [[], ["x"], ("x", 3), "abc", None],
    ids=["list", "list-str", "mixed", "str", "none"],
)
def test_a_net_with_ports_that_are_not_ids_is_left_for_freeze_to_report(ports: Any) -> None:
    """Normalising must not turn a type error into a `TypeError` or coerce a list to a tuple."""
    net = _net(ports)
    assert net.ports == ports
    draft = Draft()
    draft.add(net, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


def _conductor(a: Any, b: Any) -> Conductor:
    return Conductor(
        id=_key_id(Conductor, "c"),
        key=("c",),
        a=a,
        b=b,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def test_a_conductor_is_the_same_record_whichever_end_is_called_a() -> None:
    """Direction is not a fact: the two orders are one record, ends in id order."""
    low, high = _key_id(Port, "a"), _key_id(Port, "b")
    assert _conductor(high, low) == _conductor(low, high)
    assert (_conductor(high, low).a, _conductor(high, low).b) == tuple(sorted((low, high)))


def test_a_conductor_refuses_the_same_port_at_both_ends() -> None:
    """Exactly two ends means two different ports."""
    port = _key_id(Port, "a")
    with pytest.raises(SchemaError, match="two different ports") as excinfo:
        _conductor(port, port)
    assert excinfo.value.record_id == _key_id(Conductor, "c")


def test_a_conductor_with_ends_that_are_not_ids_is_left_for_freeze_to_report() -> None:
    """The same guard as for a net: no `TypeError`, and the values stay as given."""
    core = _conductor("x", 3)
    assert (core.a, core.b) == ("x", 3)
    draft = Draft()
    draft.add(core, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


def _port_id(digit: str) -> Id[Any]:
    return Id(kind="port", value=digit * 32)


def _draft_with_ports(*digits: str) -> Draft:
    """A draft holding an item, one function and a port for each digit."""
    item, function = _key_id(Item, "i"), _key_id(Function, "f")
    draft = Draft()
    draft.add(
        Item(
            id=item,
            key=("i",),
            part=None,
            parent=None,
            position=None,
            tag=None,
            description="",
        ),
        origin=_ORIGIN,
    )
    draft.add(
        Function(
            id=function,
            key=("f",),
            item=item,
            template=None,
            name="F",
            kind=FunctionKind.GENERIC,
        ),
        origin=_ORIGIN,
    )
    for digit in digits:
        draft.add(
            Port(
                id=_port_id(digit),
                key=(digit,),
                function=function,
                template=None,
                name=digit,
                role=PortRole.GENERIC,
            ),
            origin=_ORIGIN,
        )
    return draft


def test_alias_rewriting_keeps_a_nets_ports_in_id_order() -> None:
    """Port `1` is retired for `9`, which sorts after `5`: `freeze` rebuilds and re-sorts."""
    draft = _draft_with_ports("5", "9")
    draft.add(_net((_port_id("1"), _port_id("5"))), origin=_ORIGIN)
    draft.alias(_port_id("1"), _port_id("9"))
    net = next(iter(nets(freeze(draft)).values()))
    assert net.ports == (_port_id("5"), _port_id("9"))


def test_an_alias_that_makes_a_net_list_a_port_twice_is_a_freeze_error() -> None:
    """Both `1` and `5` become `5`: the net's own rule refuses, inside the `FreezeError`."""
    draft = _draft_with_ports("5")
    draft.add(_net((_port_id("1"), _port_id("5"))), origin=_ORIGIN)
    draft.alias(_port_id("1"), _port_id("5"))
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    assert any("twice" in str(error) for error in excinfo.value.errors)


def test_an_alias_that_makes_two_ends_of_a_conductor_one_port_is_a_freeze_error() -> None:
    """The record's own rule refusing after rewriting arrives inside the `FreezeError`."""
    draft = _draft_with_ports("5")
    draft.add(_conductor(_port_id("1"), _port_id("5")), origin=_ORIGIN)
    draft.alias(_port_id("1"), _port_id("5"))
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    assert any("two different ports" in str(error) for error in excinfo.value.errors)


def test_dataclasses_replace_renormalises_a_net() -> None:
    """`replace` runs `__post_init__` again, which is how `freeze` rewrites references."""
    low, high = sorted((_key_id(Port, "a"), _key_id(Port, "b")))
    net = _net((low, high))
    assert dataclasses.replace(net, ports=(high, low)).ports == (low, high)


def test_loading_a_net_written_in_the_wrong_order_gives_the_normalised_record() -> None:
    """`from_data` builds records through the constructor, so a hand-edited file is sorted."""
    model = core_model()
    data = json.loads(dumps(model))
    row = data["tables"]["net"][0]
    row["ports"] = row["ports"][::-1]
    reloaded = loads(json.dumps(data))
    assert reloaded == model


def test_loading_a_net_that_lists_a_port_twice_is_a_freeze_error() -> None:
    """The refusal arrives with the other per-record problems, not as a bare exception."""
    data = json.loads(dumps(core_model()))
    row = data["tables"]["net"][0]
    row["ports"] = [row["ports"][0], row["ports"][0]]
    with pytest.raises(FreezeError) as excinfo:
        loads(json.dumps(data))
    assert any("twice" in str(error) for error in excinfo.value.errors)


def test_the_vocab_package_exports_the_core_kinds_and_enums() -> None:
    """The names a caller imports from `fransys_model.vocab`."""
    for cls in _DESIGNED:
        assert getattr(vocab, cls.__name__) is cls
    for cls in (PartCategory, FunctionKind, PortRole, LinkKind, NetClass, ConductorKind, Aspect):
        assert getattr(vocab, cls.__name__) is cls


def _mate(a: Any, b: Any) -> Mate:
    return Mate(id=_key_id(Mate, "m"), key=("m",), a=a, b=b)


def test_a_mate_is_the_same_record_whichever_end_is_called_a() -> None:
    """Which connector is `a` is not a fact: two orders are one record, ends in id order."""
    low, high = _key_id(Function, "a"), _key_id(Function, "b")
    assert _mate(high, low) == _mate(low, high)
    plugged = _mate(high, low)
    assert (plugged.a, plugged.b) == tuple(sorted((low, high)))


def test_a_mate_refuses_the_same_function_at_both_ends() -> None:
    """A connector is not plugged into itself."""
    function = _key_id(Function, "a")
    with pytest.raises(SchemaError, match="two different functions") as excinfo:
        _mate(function, function)
    assert excinfo.value.record_id == _key_id(Mate, "m")


def test_a_mate_with_ends_that_are_not_ids_is_left_for_freeze_to_report() -> None:
    """The same guard as for a conductor: no `TypeError`, and the values stay as given."""
    plugged = _mate("x", 3)
    assert (plugged.a, plugged.b) == ("x", 3)
    draft = Draft()
    draft.add(plugged, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


class _SubId(Id):
    """An `Id` in all but type: the normalisation leaves it alone, and `freeze()` refuses it."""


def test_an_id_subclass_in_a_net_is_refused_at_freeze_not_left_unsorted_in_a_model() -> None:
    """The constructor only orders exact `Id`s; nothing unsorted can reach a `Model`."""
    late, early = _SubId(kind="port", value="9" * 32), _SubId(kind="port", value="1" * 32)
    net = _net((late, early))
    assert net.ports == (late, early)
    draft = Draft()
    draft.add(net, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


@pytest.mark.parametrize("bad_id", ["oops", None, 3])
def test_a_refusal_from_a_record_whose_id_is_not_an_id_names_no_record(bad_id: Any) -> None:
    """`SchemaError.record_id` is an `Id` or `None`, whatever the record held."""
    port = _key_id(Port, "a")
    with pytest.raises(SchemaError, match="twice") as excinfo:
        Net(id=bad_id, key=("n",), name=None, net_class=NetClass.GENERIC, ports=(port, port))
    assert excinfo.value.record_id is None
    with pytest.raises(SchemaError, match="two different ports") as excinfo:
        Conductor(id=bad_id, key=("c",), a=port, b=port, kind=ConductorKind.WIRE, carrier=None)
    assert excinfo.value.record_id is None
