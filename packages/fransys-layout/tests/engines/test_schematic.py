"""WP13 acceptance skeletons: the schematic engine's read and write (ROADMAP WP13, engine.md 7).

The authored and derived `layout.*` kinds live in `fransys_model.layout` (foundations.md 11,
P4). These tests use the WP14 cabinet fixture and read the model's typed accessors
`layout_of` and `derived_layout_ids`. Items are found by authoring key, never by designation.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.defaults import ENGINE_VERSION
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE, DEFAULT_SHEET
from fransys_layout.engines.schematic.write import produced_by
from fransys_layout.geometry import HintError
from fransys_layout.stages import Role
from fransys_layout.stages.columns import FUNCTION_UNPLACED_IN_COLUMN
from fransys_model.kernel import Origin, evolve, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Label,
    LinkMarker,
    Page,
    PageRole,
    Route,
    SymbolPlacement,
    derived_layout_ids,
    layout_of,
)
from fransys_model.vocab import conductors, functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _fields(record: object) -> dict[str, Any]:
    """The fields of one record by name; a missing name is a `KeyError`, not a default."""
    assert dataclasses.is_dataclass(record)
    assert not isinstance(record, type)
    return {f.name: getattr(record, f.name) for f in dataclasses.fields(record)}


def _own_numbers(record: object, pages: dict[Any, Any]) -> set[str]:
    """Every coordinate and page number `record` holds, as key-segment strings."""
    values = _fields(record)
    numbers = [values[name] for name in ("x", "y", "number") if name in values]
    if "page" in values:
        numbers.append(pages[values["page"]])
    points = values["points"] if "points" in values else ()  # noqa: SIM401 -- the explicit `in` test reads as the optional-field rule
    assert isinstance(points, tuple)
    for point in points:
        numbers += [_fields(point)["x"], _fields(point)["y"]]
    return {str(number) for number in numbers}


# each derived kind with the third segment of its keys (a page key begins with its drawing set's)
_DERIVED = {
    DrawingSet: "drawing_set",
    Page: "drawing_set",
    SymbolPlacement: "symbol_placement",
    Route: "route",
    LinkMarker: "link_marker",
    Label: "label",
}


def test_stage_role_and_model_page_role_have_equal_member_names() -> None:
    """`write/sets.py` converts `Role` to `layout.PageRole` by member name too."""
    assert {member.name for member in Role} == {member.name for member in PageRole}


def test_read_uses_the_defaults_when_no_profile_is_authored() -> None:
    """The cabinet authors no profile or sheet format: the house conventions apply."""
    inputs = read_inputs(freeze(build_cabinet()))
    assert inputs.profile == DEFAULT_PROFILE
    assert inputs.sheet == DEFAULT_SHEET


def test_read_outputs_are_sorted_and_order_free() -> None:
    """Every tuple `read_inputs` returns is sorted, so authoring order cannot leak in."""
    forward = read_inputs(freeze(build_cabinet()))
    backward = read_inputs(freeze(build_cabinet(reverse=True)))
    assert forward == backward


def test_read_skips_cable_functions_and_draws_not_installed_items() -> None:
    """Cable items are not drawn; a board's `CONNECTOR` is, when wired, its other items are not
    (model-0040, spec B1); an `installed=False` item is drawn.

    D8: an idle connector is not drawn, and the cabinet's board `A1` has one unwired `CONNECTOR`
    (a wired board connector is drawn: `test_board_internal`).
    """
    model = freeze(build_cabinet())
    drawn_items = {spec.item for spec in read_inputs(model).functions}
    by_key = {item.key: item.id for item in items(model).values()}
    assert by_key[("cabinet", "w1")] not in drawn_items
    assert by_key[("cabinet", "a1")] not in drawn_items
    assert by_key[("cabinet", "a1", "f1")] not in drawn_items
    assert by_key[("cabinet", "k8")] in drawn_items


def test_a_net_without_conductors_is_read_as_one_net_group() -> None:
    """No spanning tree is built while reading: the declared net arrives whole."""
    inputs = read_inputs(freeze(build_cabinet()))
    (group,) = inputs.net_groups
    assert len(group.ports) == 2
    assert list(group.ports) == sorted(group.ports, key=lambda ref: (ref.port,))


def test_every_connection_endpoint_is_a_port_of_a_drawn_function() -> None:
    """Endpoints are ids end to end: each one belongs to a function that is drawn."""
    inputs = read_inputs(freeze(build_cabinet()))
    drawn_functions = {spec.function for spec in inputs.functions}
    for connection in inputs.connections:
        assert connection.a.function in drawn_functions
        assert connection.b.function in drawn_functions


def _across_two_drawing_sets() -> Model:
    """The cabinet laid out with `=P2` in a second drawing set: all six derived kinds are filled.

    On the default sheet `=P1` and `=P2` share a page, so nothing is severed and there is no
    `layout.link_marker`; a second location cuts the K1 to K2 signal.
    """
    model, _ = lay_out_schematic(freeze(build_cabinet(second_location=True)))
    return model


def _subject_key(model: Model, record: object) -> tuple[str, ...]:
    """The authoring key of the record a derived record is about, which its own key starts with."""
    values = _fields(record)
    if values.get("net") is not None:  # a net-realised route: its two ports, in id order
        return (*ports(model)[values["a"]].key, *ports(model)[values["b"]].key)
    for field, table in (("function", functions), ("conductor", conductors), ("port", ports)):
        subject = values.get(field)
        if subject is not None:
            return table(model)[subject].key
    return ()


def test_engine_writes_every_derived_kind_with_produced_by() -> None:
    """A run fills every derived table and stamps each record with the engine version."""
    model = _across_two_drawing_sets()
    for record_type in _DERIVED:
        records = layout_of(model, record_type).values()
        assert records
        assert all(_fields(record)["produced_by"] == produced_by() for record in records)


def test_produced_by_names_engine_and_version() -> None:
    """The stamp is `fransys-layout/schematic <version>`, `ENGINE_VERSION` (decision
    layout-0029; layout-0046 amended layout-0020, so a release bumps `ENGINE_VERSION` for this
    exact reason -- kept dynamic, not a hardcoded literal, so a release does not break this
    test the way it once broke this one when it was still `"fransys-layout/schematic
    0.0.0"`).
    """
    assert produced_by() == f"fransys-layout/schematic {ENGINE_VERSION}"


def test_derived_keys_hold_no_page_number_or_position() -> None:
    """Ids survive repagination.

    No discriminator segment of any derived record is one of that record's own coordinates or
    page numbers. The segments of the subject's own authoring key are the model's, and may be
    numbers (terminal `1`); the kind is the short name (model layout-namespace.md).
    """
    model = _across_two_drawing_sets()
    pages = {page.id: _fields(page)["number"] for page in layout_of(model, Page).values()}
    for record_type, short in _DERIVED.items():
        for record in layout_of(model, record_type).values():
            assert record.key[:3] == ("layout", "schematic", short)
            subject = _subject_key(model, record)
            assert record.key[3 : 3 + len(subject)] == subject
            if record_type is LinkMarker:
                # its whole discriminator is model segments (port key, side, a partner's port
                # key or a placement's discriminator), which the sibling test below pins
                continue
            assert not set(record.key[3 + len(subject) :]) & _own_numbers(record, pages)


def test_a_link_marker_key_ends_in_its_port_key_side_and_its_partner_or_placement() -> None:
    """The docs/design/engine.md 7 discriminator (model-0025, layout-0022, layout-0052).

    A pair marker is its port key, its side and its partner's port key. An off stub is its own
    partner, so it ends in its far port's key (layout-0057). A star marker, a reference (also
    one that carries a stub's text), a branch, names no partner and no role (the role is a
    field, never in the key): its port key, the segment `star`, and its placement's
    discriminator, nothing for a home placement and the column's group key for a replica. A
    leaving line's one stub (HL18) is `line_stub`, its line's item key and `branch` and number.
    """
    # the second location has stubs and a merged reference; the extra relay cuts a wire (a pair)
    models = (
        _across_two_drawing_sets(),
        lay_out_schematic(freeze(build_cabinet(extra_relay=True)))[0],
    )
    kinds = set()
    for model in models:
        markers = layout_of(model, LinkMarker)
        assert markers
        stands = layout_of(model, SymbolPlacement).values()
        for marker in markers.values():
            values = _fields(marker)
            if marker.key[3] == "line_stub":
                line = items(model)[values["carrier"]].key
                assert marker.key[4 : 5 + len(line)] == (*line, "branch")
                assert marker.key[5 + len(line)].isdigit()
                assert values["partner"] == marker.id
                kinds.add("line_stub")
                continue
            port = ports(model)[values["port"]]
            partner = markers[values["partner"]]
            is_star = marker.star is not None and partner.id != marker.id
            head = (*port.key, "star" if is_star else values["side"].value)
            assert marker.key[3 : 3 + len(head)] == head
            tail = marker.key[3 + len(head) :]
            if marker.star is None:
                assert tail == ports(model)[_fields(partner)["port"]].key
                kinds.add("pair")
            elif partner.id == marker.id:
                assert tail == ports(model)[values["far"]].key
                kinds.add("off")
            else:
                # the discriminator the marker's own placement carries on this page: what follows
                # the function's key in that placement's key (`write/placements.py`)
                function = ports(model)[values["port"]].function
                width = 3 + len(functions(model)[function].key)
                actual = {
                    one.key[width:]
                    for one in stands
                    if one.function == function and one.page == values["page"]
                }
                assert actual
                assert tail in actual
                kinds.add("star")
    assert kinds == {"pair", "off", "star", "line_stub"}


def test_a_terminal_on_two_pages_has_two_placements_with_different_ids() -> None:
    """One subject, several records: the replica column's group key tells them apart."""
    model, _ = lay_out_schematic(freeze(build_cabinet()))
    by_function: dict[object, list[object]] = {}
    for placement in layout_of(model, SymbolPlacement).values():
        by_function.setdefault(_fields(placement)["function"], []).append(placement.id)
    ids = max(by_function.values(), key=len)
    assert len(ids) > 1
    assert len(set(ids)) == len(ids)


def test_a_stale_derived_record_is_removed() -> None:
    """Replace, never patch: a derived record that no run would write is gone after one."""
    once, _ = lay_out_schematic(freeze(build_cabinet()))
    (first, *_) = layout_of(once, SymbolPlacement).values()
    key = ("layout", "schematic", "symbol_placement", "stale")
    stale = dataclasses.replace(first, id=make_id(SymbolPlacement, key), key=key)
    seeded = evolve(once, put=(stale,), origin=Origin(file="test", line=1, note="stale"))
    assert stale.id in derived_layout_ids(seeded)
    again, _ = lay_out_schematic(seeded)
    assert stale.id not in derived_layout_ids(again)
    assert again.digests["layout"] == once.digests["layout"]


def test_a_rerun_replaces_results_and_never_accumulates() -> None:
    """Replace, never patch: a second run leaves the same number of derived records."""
    once, _ = lay_out_schematic(freeze(build_cabinet(second_location=True)))
    twice, _ = lay_out_schematic(once)
    for record_type in _DERIVED:
        assert len(layout_of(twice, record_type)) == len(layout_of(once, record_type))
    assert derived_layout_ids(twice) == derived_layout_ids(once)


def test_findings_are_returned_sorted_and_the_design_still_draws() -> None:
    """The unchained function is reported, and the model is laid out all the same."""
    model, findings = lay_out_schematic(freeze(build_cabinet()))
    assert FUNCTION_UNPLACED_IN_COLUMN in [f.code for f in findings]
    assert list(findings) == sorted(findings, key=lambda f: (f.code, f.subjects))
    assert layout_of(model, Page)


def test_a_chain_hint_that_contradicts_the_model_raises_a_layout_error() -> None:
    """Structural problems raise: a chain whose functions are not connected is refused."""
    model = freeze(build_cabinet(broken_chain=True))
    with pytest.raises(HintError):
        run_stages(model, read_inputs(model))
