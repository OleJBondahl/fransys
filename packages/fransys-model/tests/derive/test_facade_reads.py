"""Tests: the facade's reads of a model, as derive facts (decision 0221).

One invented plant, frozen once for the module: a cabinet holding a panel, the panel holding a
rail, a sibling unit `other`, a pump and a relay part with a changeover function and pin
templates, and three documents (cabinet, panel, other).
"""

import pytest
from plant import Plant

from fransys_model.derive import (
    changeover_functions,
    document_ids,
    document_stems,
    has_documents,
    has_project,
    is_unit_owned_kind,
    listing_interface,
    listing_revision_text,
    part_function_pins,
    part_records,
    record_key_text,
    release_names,
    subject_kind_text,
    subject_part_mpn,
    unit_chain_below,
    unit_ids,
    unit_key,
    unit_owned_ids,
)
from fransys_model.derive.rows_baseline import BaselineUnit, Listing
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab import Document, DocumentPreset
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import FunctionKind, PortRole
from fransys_model.vocab.project import Project
from fransys_model.vocab.tables import documents, parts
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate

CABINET = make_id(Unit, ("cabinet",))
PANEL = make_id(Unit, ("panel",))
RAIL = make_id(Unit, ("rail",))
OTHER = make_id(Unit, ("other",))
CAB_ITEM = make_id(Item, ("cab_item",))
CAB_FN = make_id(Function, ("cab_item", "cab_fn"))
CAB_PORT = make_id(Port, ("cab_item", "cab_fn", "p1"))
PANEL_ITEM = make_id(Item, ("panel_item",))
RAIL_ITEM = make_id(Item, ("rail_item",))
RAIL_FN = make_id(Function, ("rail_item", "rail_fn"))
OTHER_ITEM = make_id(Item, ("other_item",))
PUMP_ITEM = make_id(Item, ("pump",))
PUMP_FN = make_id(Function, ("pump", "pump_fn"))
BARE_FN = make_id(Function, ("bare", "bare_fn"))
RELAY_PART = make_id(Part, ("part-K",))
PUMP_PART = make_id(Part, ("part-P",))
CABINET_DOC = make_id(Document, ("docs", "cabinet"))
PANEL_DOC = make_id(Document, ("docs", "panel"))
OTHER_DOC = make_id(Document, ("docs", "other"))
NET = make_id(Net, ("n_24v",))


def _template(
    plant: Plant, name: str, kind: FunctionKind, pins: tuple[str, ...]
) -> FunctionTemplate:
    """A function template of the relay part, with one generic pin template per name in `pins`."""
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("relay", name)),
        key=("relay", name),
        part=RELAY_PART,
        name=name,
        kind=kind,
    )
    plant.add(template)
    for pin in pins:
        plant.add(
            PortTemplate(
                id=make_id(PortTemplate, ("relay", name, pin)),
                key=("relay", name, pin),
                function=template.id,
                name=pin,
                role=PortRole.GENERIC,
            )
        )
    return template


def _document(key: tuple[str, str], unit: Id[Unit]) -> Document:
    """A cabinet schematic document about `unit`, with no texts."""
    return Document(
        id=make_id(Document, key),
        key=key,
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=None,
        item=None,
        add=(),
        remove=(),
        cover="",
        notes=None,
        unit=unit,
    )


@pytest.fixture(scope="module")
def model() -> Model:
    """The invented plant of this module, frozen once."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    panel = plant.unit("panel", name="panel", parent=cabinet)
    rail = plant.unit("rail", name="rail", parent=panel)
    other = plant.unit("other", name="other")
    for key, unit in (("cab", cabinet), ("panel", panel), ("rail", rail), ("other", other)):
        plant.port(plant.function(plant.item(f"{key}_item", unit=unit), f"{key}_fn"), "p1")
    relay = plant.part("K")
    contact = _template(plant, "3", FunctionKind.CONTACT_CO, ("10", "2"))
    _template(plant, "12", FunctionKind.GENERIC, ("1",))
    relay_item = plant.item("relay", part=relay, unit=cabinet)
    plant.function(relay_item, "relay_co", template=contact.id, kind=FunctionKind.CONTACT_CO)
    pump = plant.part("P")
    plant.function(plant.item("pump", part=pump, unit=cabinet), "pump_fn")
    plant.function(plant.item("bare"), "bare_fn")
    plant.net("n_24v", ())
    plant.add(
        _document(("docs", "cabinet"), cabinet),
        _document(("docs", "panel"), panel),
        _document(("docs", "other"), other),
        Project(
            id=make_id(Project, ("project",)),
            key=("project",),
            title="Invented pump station",
            number="P-0001",
            customer="Example Co",
            revision=1,
            author="Example",
        ),
    )
    return plant.model()


def test_unit_ids_are_the_four_units_sorted(model: Model) -> None:
    """Every unit id, sorted: the four planted units."""
    assert unit_ids(model) == tuple(sorted((CABINET, PANEL, RAIL, OTHER)))


def test_unit_key_is_the_authoring_key(model: Model) -> None:
    """The key of the cabinet unit is its one-part key."""
    assert unit_key(model, CABINET) == ("cabinet",)


def test_unit_chain_below_stops_at_the_given_unit(model: Model) -> None:
    """The rail, its panel, and no cabinet: the chain stops before the given unit."""
    assert unit_chain_below(model, CABINET, RAIL) == [RAIL, PANEL]


def test_unit_chain_below_none_goes_to_the_top(model: Model) -> None:
    """With no unit, the chain of the rail runs to the top-level cabinet."""
    assert unit_chain_below(model, None, RAIL) == [RAIL, PANEL, CABINET]


def test_unit_chain_below_the_subject_itself_is_empty(model: Model) -> None:
    """A subject that is the given unit has an empty chain below it."""
    assert unit_chain_below(model, RAIL, RAIL) == []


def test_unit_owned_ids_of_the_cabinet_hold_its_subtree_not_a_sibling(model: Model) -> None:
    """The cabinet owns its items, function, port, documents and nested units; not `other`."""
    owned = unit_owned_ids(model, CABINET)
    for kept in (CAB_ITEM, CAB_FN, CAB_PORT, PANEL, RAIL, RAIL_ITEM, RAIL_FN, PUMP_ITEM, PUMP_FN):
        assert kept in owned
    assert CABINET_DOC in owned
    for dropped in (OTHER, OTHER_ITEM, OTHER_DOC):
        assert dropped not in owned


def test_unit_owned_ids_of_a_nested_unit_leave_out_its_parent(model: Model) -> None:
    """The panel owns the rail's subtree and its own document, but not the cabinet's items."""
    owned = unit_owned_ids(model, PANEL)
    assert {PANEL, RAIL, PANEL_ITEM, RAIL_ITEM, PANEL_DOC} <= owned
    assert CAB_ITEM not in owned
    assert CABINET_DOC not in owned


def test_document_ids_are_the_three_planted_documents(model: Model) -> None:
    """Every document id once; the table's order is not the plant's insertion order."""
    assert sorted(document_ids(model)) == sorted((CABINET_DOC, PANEL_DOC, OTHER_DOC))
    assert document_ids(model) == tuple(documents(model))


def test_document_stems_pair_each_document_with_its_name(model: Model) -> None:
    """Each document id with its name, the second part of its key, in the id order given."""
    stems = dict(document_stems(model))
    assert stems == {CABINET_DOC: "cabinet", PANEL_DOC: "panel", OTHER_DOC: "other"}
    assert [one for one, _name in document_stems(model)] == list(document_ids(model))


def test_has_documents_and_has_project_are_true_for_the_plant(model: Model) -> None:
    """The plant holds documents and its one project."""
    assert has_documents(model)
    assert has_project(model)


def test_an_empty_model_has_no_documents_and_no_project() -> None:
    """A model with nothing in it has neither."""
    empty = Plant().model()
    assert not has_documents(empty)
    assert not has_project(empty)


def test_release_names_are_one_per_planted_unit(model: Model) -> None:
    """One release name per planted unit; the table's order is not the insertion order."""
    assert sorted(release_names(model)) == ["cabinet", "other", "panel", "rail"]


def test_subject_part_mpn_of_an_item_and_of_its_function(model: Model) -> None:
    """The pump item and its function both give the pump's mpn."""
    assert subject_part_mpn(model, PUMP_ITEM) == "EXAMPLE-P"
    assert subject_part_mpn(model, PUMP_FN) == "EXAMPLE-P"


def test_subject_part_mpn_is_none_without_a_part(model: Model) -> None:
    """The bare function's item has no part, so no mpn."""
    assert subject_part_mpn(model, BARE_FN) is None


def test_part_records_are_the_plants_parts(model: Model) -> None:
    """The two planted parts, by mpn."""
    assert sorted(part.mpn for part in part_records(model)) == ["EXAMPLE-K", "EXAMPLE-P"]
    assert part_records(model) == tuple(parts(model).values())


def test_part_function_pins_sort_functions_and_pins_by_marking(model: Model) -> None:
    """Pins `10` and `2` sort as 2 then 10, and functions `3` then `12`."""
    assert part_function_pins(model) == {
        RELAY_PART: [("3", ["2", "10"]), ("12", ["1"])],
    }


def test_changeover_functions_is_the_one_contact_co_template(model: Model) -> None:
    """Only the CONTACT_CO template `3` of the relay part is a changeover function."""
    assert changeover_functions(model) == {(RELAY_PART, "3")}


def test_subject_kind_text_names_each_handle_kind() -> None:
    """A net, a unit and an item give their kind text."""
    assert subject_kind_text(NET) == "net"
    assert subject_kind_text(CABINET) == "unit"
    assert subject_kind_text(PUMP_ITEM) == "item"


def test_record_key_text_of_a_net_is_its_key(model: Model) -> None:
    """The net's record key joined with `/`, and a unit's key the same way."""
    assert record_key_text(model, NET) == "n_24v"
    assert record_key_text(model, PANEL) == "panel"


def test_is_unit_owned_kind_is_true_for_an_item_and_false_for_a_net() -> None:
    """An item is owned by a unit; a net is not."""
    assert is_unit_owned_kind(PUMP_ITEM)
    assert not is_unit_owned_kind(NET)


def test_listing_interface_and_revision_text_of_a_listing() -> None:
    """The interface is the unit's text as given; the revision prints as `version.revision`."""
    listing = Listing(
        unit=BaselineUnit(name="cabinet", version=2, revision=10, interface="24 V DC"),
        items=(),
        units=(),
        boundary=(),
        conductors=(),
        mates=(),
        nets=(),
    )
    assert listing_interface(listing) == "24 V DC"
    assert listing_revision_text(listing) == "2.10"
