"""Layout properties on the written cabinet: terminals per page, marker pairs, Documents."""

from collections import defaultdict
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import text_width
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_model.kernel import Origin, freeze, make_id
from fransys_model.layout import MarkerSide as ModelMarkerSide
from fransys_model.layout import Profile, SheetFormat
from fransys_model.vocab import AspectNode, Document, DocumentPreset, documents

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.read import StageInputs
    from fransys_layout.stages.types import LinkMarker as StageLinkMarker
    from fransys_model.kernel import Model

_ORIGIN = Origin(file="tests/engines/test_properties_layout.py", line=1, note="properties")
_X2 = ("cabinet", "x2", "1", "fn", "terminal")
_BASE = ("layout", "schematic", "symbol_placement", *_X2)
_C1 = make_id(AspectNode, ("c1",))


def _narrow(width_mm: int) -> tuple[SheetFormat, Profile]:
    """A sheet `width_mm` wide with the default profile on it."""
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("test", "sheet")),
        key=("test", "sheet"),
        name="narrow",
        width_mm=width_mm + 20,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    profile = Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        sheet_format=sheet.id,
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        text_height=DEFAULT_PROFILE.text_height,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    return sheet, profile


@cache
def _run(
    width_mm: int | None = None, *, second_location: bool = False
) -> tuple[Model, Model, StageInputs, StageResults]:
    """The frozen cabinet, its laid-out model, the read inputs and the stage results."""
    draft = build_cabinet(second_location=second_location)
    if width_mm is not None:
        draft.extend(_narrow(width_mm), origin=_ORIGIN)
    model = freeze(draft)
    laid_out, _ = lay_out_schematic(model)
    inputs = read_inputs(model)
    return model, laid_out, inputs, stage_results(model, inputs)[0]


def _table(model: Model, name: str) -> dict:
    return dict(model.tables[name])


def _length(marker: StageLinkMarker) -> int:
    """The box's extent along its text: a vertical box (M1, N or S pin) is the turned frame."""
    return marker.box.height if marker.vertical else marker.box.width


@pytest.mark.parametrize(
    ("width_mm", "groups"), [(None, {"p1"}), (250, {"p1", "p2"})], ids=["default", "250mm"]
)
def test_a_terminal_used_from_two_groups_is_placed_once_on_each_page(
    width_mm: int | None, groups: set[str]
) -> None:
    """Every terminal function has one placement per page; a replica's key adds group and set."""
    model, out, _, results = _run(width_mm)
    functions = _table(model, "function").values()
    terminals = {f.id for f in functions if f.kind.value == "terminal"}
    pages = defaultdict(list)
    keys = defaultdict(set)
    for placement in _table(out, "layout.symbol_placement").values():
        if placement.function in terminals:
            pages[placement.function].append(placement.page)
            keys[placement.function].add(placement.key)
    assert set(pages) == terminals
    for function, on in pages.items():
        assert len(on) == len(set(on))
        assert len(on) == sum(one.function == function for one in results.layout.placed)
    (x2,) = (f.id for f in functions if f.key == _X2)
    assert len(pages[x2]) == len(groups) + 1
    assert keys[x2] == {_BASE, *((*_BASE, group, "drawing_set", "c1") for group in groups)}


_SIGNAL = (
    ("cabinet", "k1", "fn", "aux", "port", "14"),
    ("cabinet", "k2", "fn", "aux", "port", "13"),
)


def _signal_ports(model: Model) -> tuple:
    """The ports of the K1:14 to K2:13 signal, by authoring key."""
    port_of = {port.key: id_ for id_, port in model.tables["port"].items()}
    return tuple(port_of[key] for key in _SIGNAL)


def test_a_wire_cut_by_a_page_break_has_a_marker_pair_that_says_where_its_partner_is() -> None:
    """links.md 6.6 stands under D9: a net of 3 or more ports is D9's, a cut 2-port wire is a pair.

    On the 250 mm sheet every group has a page of its own, `=P1` first, so the K1:14 to K2:13
    wire runs from page 1 to page 2. Its owner marker is at the earlier page, the two point at
    each other, and each box is the sheet's fixed reference length (LD3 (c)), never measured,
    one line thick (M1: a vertical box is the turned frame, its length its height).
    """
    model, out, inputs, results = _run(250)
    k1, k2 = _signal_ports(model)
    pair = [marker for marker in results.layout.markers if not marker.star]
    assert {marker.port for marker in pair} == {k1, k2}
    records = {id_: m for id_, m in _table(out, "layout.link_marker").items() if m.port in {k1, k2}}
    assert len(records) == 2
    for record in records.values():
        partner = records[record.partner]
        assert records[partner.partner] is record
        assert {record.side, partner.side} == {ModelMarkerSide.OWNER, ModelMarkerSide.USER}
    owner, user = sorted(pair, key=lambda marker: marker.page)
    assert (owner.port, owner.side.name, owner.page) == (k1, "OWNER", 1)
    assert (user.port, user.side.name, user.page) == (k2, "USER", 2)
    assert (owner.partner_page, user.partner_page) == (2, 1)
    length = reference_box_width(inputs.sheet, inputs.profile)
    thickness = inputs.profile.text_height + 2 * inputs.profile.marker_padding
    for one in pair:
        assert one.vertical
        assert _length(one) == length
        assert one.box.width == thickness
        (record,) = (r for r in records.values() if r.port == one.port)
        assert (record.width, record.height) == (one.box.width, one.box.height)


def test_a_conductor_between_two_locations_ends_in_a_stub_label_at_each_end() -> None:
    """D10, D13: across two locations the K1:14 to K2:13 conductor is no owner/user pair.

    Each end carries a stub label in its own drawing set, an arrow and the far end's location
    (`+C1`, `+C2`) and port, and its box, vertical on an N or S pin (M1), is as long as its
    measured text plus the marker padding.
    """
    model, out, inputs, results = _run(second_location=True)
    k1, k2 = _signal_ports(model)
    markers = results.layout.markers
    assert not [m for m in markers if not m.star and m.port in {k1, k2}]
    stubs = {m.port: m for m in markers if m.star == "off" and m.port in {k1, k2}}
    assert set(stubs) == {k1, k2}
    assert stubs[k1].drawing_set != stubs[k2].drawing_set
    label_of = {loc.location: loc.label for loc in inputs.locations}
    labels = {
        plan.drawing_set: label_of[plan.location]
        for plan in results.layout.pages
        if plan.location is not None
    }
    padding = inputs.profile.marker_padding
    for near, far, far_port in ((k1, k2, "K2:13"), (k2, k1, "K1:14")):
        stub = stubs[near]
        assert f"+{labels[stubs[far].drawing_set]}" in stub.text
        assert stub.text.endswith(far_port)
        assert any(arrow in stub.text for arrow in "←→")
        width = text_width(stub.text, height=inputs.profile.text_height) + 2 * padding
        assert _length(stub) == width
    assert len(_table(out, "layout.link_marker")) == len(markers)


def test_a_two_location_marker_is_wider_than_its_text_without_the_prefix() -> None:
    """The prefix is in the box: dropping it would make the box shorter."""
    _, _, inputs, results = _run(second_location=True)
    height = inputs.profile.text_height
    assert results.layout.markers
    for marker in results.layout.markers:
        plain = f"/{marker.partner_page}.8"  # the widest column digit
        assert _length(marker) > text_width(plain, height=height)


def test_a_location_with_no_authored_document_is_laid_out_and_a_document_changes_no_layout() -> (
    None
):
    """A `Document` is core, joined to a drawing set by location only; layout never reads it."""
    model, out, _, _ = _run()
    assert not documents(model)
    assert _C1 in {s.location for s in _table(out, "layout.drawing_set").values()}
    draft = build_cabinet()
    key = ("cabinet", "document")
    draft.extend(
        (
            Document(
                id=make_id(Document, key),
                key=key,
                preset=DocumentPreset.CABINET_SCHEMATIC,
                location=_C1,
                item=None,
                add=(),
                remove=(),
                cover="# invented cabinet",
                notes=None,
            ),
        ),
        origin=_ORIGIN,
    )
    with_document = freeze(draft)
    laid_out, _ = lay_out_schematic(with_document)
    assert documents(with_document)
    assert with_document.digests["core"] != model.digests["core"]
    assert laid_out.digests["layout"] == out.digests["layout"]
