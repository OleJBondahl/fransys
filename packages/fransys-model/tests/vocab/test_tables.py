"""WP8 tests: typed accessors over `Model.tables` (ROADMAP WP8, design/kernel-model.md 5.5 and
design/derive.md)."""

from typing import TYPE_CHECKING, Any

import pytest
from examples import core_model, relay_part_bundle

from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import (
    Draft,
    Model,
    Origin,
    Record,
    SchemaError,
    evolve,
    freeze,
    make_id,
)
from fransys_model.vocab.core import Item
from fransys_model.vocab.facets import SupplyFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import (
    aspect_nodes,
    conductors,
    facet_subject,
    facets_of,
    function_templates,
    functions,
    internal_links,
    items,
    kind_of,
    mates,
    nets,
    parts,
    placements,
    port_templates,
    ports,
    projects,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_tables.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def test_parts_returns_a_correctly_typed_table() -> None:
    """`parts(model)` returns every `Part`, keyed by its own id, typed as `Id[Part]` -> `Part`."""
    bundle = relay_part_bundle()
    model = _freeze((bundle.part,))
    table = parts(model)
    assert table[bundle.part.id] is bundle.part


def test_function_templates_returns_every_template() -> None:
    """`function_templates(model)` returns all three of the relay bundle's templates."""
    bundle = relay_part_bundle()
    model = _freeze((bundle.part, *bundle.function_templates))
    table = function_templates(model)
    assert set(table) == {template.id for template in bundle.function_templates}


def test_facets_of_is_generic_over_facet_type() -> None:
    """`facets_of(model, TerminalFacet)` keys results by the facet's own id, not its subject."""
    bundle = relay_part_bundle()
    model = _freeze((bundle.part,))
    table = facets_of(model, TerminalFacet)
    assert table == {}


_ACCESSORS: list[tuple[Callable[[Model], Any], str]] = [
    (parts, "part"),
    (function_templates, "function_template"),
    (port_templates, "port_template"),
    (internal_links, "internal_link"),
    (items, "item"),
    (functions, "function"),
    (ports, "port"),
    (nets, "net"),
    (conductors, "conductor"),
    (mates, "mate"),
    (aspect_nodes, "aspect_node"),
    (placements, "placement"),
    (projects, "project"),
]


@pytest.mark.parametrize(("accessor", "kind"), _ACCESSORS, ids=[kind for _, kind in _ACCESSORS])
def test_an_accessor_returns_the_models_own_table_of_its_kind(
    accessor: Callable[[Model], Any], kind: str
) -> None:
    """Nothing is copied, and each accessor reads the kind it is named for."""
    model = core_model()
    assert accessor(model) is model.tables[kind]


@pytest.mark.parametrize(("accessor", "kind"), _ACCESSORS, ids=[kind for _, kind in _ACCESSORS])
def test_an_accessor_keys_every_record_by_its_own_id(
    accessor: Callable[[Model], Any], kind: str
) -> None:
    """The key is the record's `id`, and the record is of the accessor's kind."""
    table = accessor(core_model())
    assert table
    for target, found in table.items():
        assert found.id == target
        assert target.kind == kind


@pytest.mark.parametrize(("accessor", "kind"), _ACCESSORS, ids=[kind for _, kind in _ACCESSORS])
def test_an_accessor_returns_an_empty_table_for_a_model_without_that_kind(
    accessor: Callable[[Model], Any], kind: str
) -> None:
    """No `KeyError` for a kind that has no records yet."""
    empty = freeze(Draft())
    assert accessor(empty) == {}
    assert kind not in empty.tables


def test_facets_of_returns_the_facets_keyed_by_their_own_id() -> None:
    """Keyed by the facet's id, so two facets of one subject would not overwrite each other."""
    model = core_model()
    (relay,) = (
        item for item in items(model).values() if own_designation_or_none(model, item) == "-K1"
    )
    facet = TerminalFacet(
        id=make_id(TerminalFacet, ("plant", "k1", "terminal")),
        key=("plant", "k1", "terminal"),
        subject=relay.id,
        group="L1",
        index=0,
    )
    with_facet = evolve(
        model, put=(facet,), origin=Origin(file="test_tables.py", line=1, note="facet")
    )
    assert facets_of(with_facet, TerminalFacet) == {facet.id: facet}
    assert facets_of(model, TerminalFacet) == {}


def test_facets_of_refuses_a_kind_outside_the_facet_namespace() -> None:
    """`Item` is a record, but not a facet."""
    with pytest.raises(SchemaError, match="not a facet") as excinfo:
        facets_of(core_model(), Item)
    assert excinfo.value.kind == "item"


@pytest.mark.parametrize("facet_type", [int, str, object])
def test_facets_of_refuses_a_class_that_is_not_a_record(facet_type: type) -> None:
    """A `SchemaError` for the caller's mistake, not a `KeyError` or an `AttributeError`."""
    with pytest.raises(SchemaError, match="not a @record class"):
        facets_of(core_model(), facet_type)


def test_facets_of_refuses_an_instance_and_other_things_that_are_not_classes() -> None:
    """Passing the record instead of its class is the obvious slip: a `SchemaError`."""
    model = core_model()
    an_item: Any = next(iter(items(model).values()))
    for not_a_class in (an_item, "facet.terminal", None, 3):
        bad: Any = not_a_class
        with pytest.raises(SchemaError, match="not a @record class"):
            facets_of(model, bad)


def test_kind_of_refuses_a_class_that_is_not_a_record() -> None:
    """A class not decorated with `@record` carries no `__kind__`: `.kind` names the class."""

    class NotARecord:
        pass

    with pytest.raises(SchemaError, match="not a @record class") as excinfo:
        kind_of(NotARecord)
    assert excinfo.value.kind == NotARecord.__qualname__


@pytest.mark.parametrize("not_a_class", [3, "abc"])
def test_kind_of_refuses_something_that_is_not_a_class(not_a_class: Any) -> None:
    """Passing an instance, not a class: `.kind` shows its `repr`, not a class's name."""
    with pytest.raises(SchemaError, match="not a @record class") as excinfo:
        kind_of(not_a_class)
    assert excinfo.value.kind == repr(not_a_class)


def test_facet_subject_reads_the_field_the_kind_declared() -> None:
    """The id a facet describes, whatever the kind calls that field."""
    subject = make_id(Item, ("plant", "x"))
    terminal = TerminalFacet(
        id=make_id(TerminalFacet, ("t",)), key=("t",), subject=subject, group="L1", index=1
    )
    assert facet_subject(terminal) is subject
    part = relay_part_bundle().part.id
    supply = SupplyFacet(
        id=make_id(SupplyFacet, ("s",)),
        key=("s",),
        subject=part,
        supplier="Example Distributor",
        supplier_part_number="EX-1",
        note="",
    )
    assert facet_subject(supply) is part


def test_facet_subject_refuses_a_record_that_is_not_a_facet() -> None:
    """An item declares no subject: a `SchemaError` naming its class, not an `AttributeError`."""
    item = next(iter(items(core_model()).values()))
    with pytest.raises(SchemaError, match="declares no subject") as excinfo:
        facet_subject(item)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == item.id
    assert str(excinfo.value).startswith(type(item).__qualname__)
