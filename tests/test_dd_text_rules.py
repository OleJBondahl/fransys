"""F5-C undo tests for D12 (designation text) and D15 (other drawing rules), through the facade.

Public reads only: `layout.*` records, `label_text`, `page_title` and the rendered SVG of
`fransys_render.pages`; nothing reads `ext` or a private name. Each test carries a
`# UNDO:` line, the one mutation that must make it fail.

Fixtures: `test_units_worked_example._build_system` (two pump cabinets and two board units),
`_relay_pair` (two relays and a terminal strip), `_sibling_units` (two units with a relay each
in one shared top-level group) and the layout package's `layout_cabinet` (two crossings).
"""

import functools
import importlib.util
import itertools
import re
import sys
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys_render import pages as render_pages

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic import engine
from fransys_model.derive import drawing_text, unit_release
from fransys_model.derive.closure import net_of
from fransys_model.derive.designation import (
    item_designation,
    own_designation_or_none,
    own_nodes,
    reference_designation,
    terminal_designation,
)
from fransys_model.derive.drawing_text import (
    is_device_terminal,
    item_tag_text,
    label_text,
    page_title,
    point_text,
    run_point_text,
    strip_tag_text,
    unit_tag_text,
)
from fransys_model.kernel import Severity, freeze
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Page,
    Route,
    SymbolPlacement,
    default_sheet_format,
    layout_of,
)
from fransys_model.vocab import Aspect
from fransys_model.vocab.enums import ConductorKind, FunctionKind
from fransys_model.vocab.tables import aspect_nodes, conductors, functions, items, units

_ROOT_TESTS = Path(__file__).parent
_PROJECT: dict[str, Any] = {
    "title": "Text rules",
    "number": "P-1003",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def _system_model():
    return _load(_ROOT_TESTS / "test_units_worked_example.py")._build_system()[0].model


def _labels(model, *, own_set: bool | None = None, kind=LabelKind.TAG, slot=None):
    """Labels of one kind (and slot prefix), in unit sets, top-level sets, or both (None)."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return [
        lb
        for lb in layout_of(model, Label).values()
        if lb.kind is kind
        and (slot is None or lb.slot.startswith(slot))
        and (own_set is None or (sets[pages[lb.page].drawing_set].unit is not None) == own_set)
    ]


def _labels_in_unit_sets(model, unit_name, **kwargs):
    """Labels in the own sets of every unit instance called `unit_name` (two pumps, two boards)."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return [
        lb
        for lb in _labels(model, **kwargs)
        if (unit := sets[pages[lb.page].drawing_set].unit) is not None
        and unit_release(model, unit).name == unit_name
    ]


# -- D12 ------------------------------------------------------------------------------------


def test_a_components_tag_in_a_units_own_set_is_its_item_designation_only() -> None:
    """D12: unit-set tags carry no "+" or "=" and read "-X2" and "-K1"."""
    # UNDO: fransys_model/derive/drawing_text.py: `unit_tag_text` returns `reference_designation`
    #   (the aspects) again
    model = _system_model()
    cabinet = _labels_in_unit_sets(model, "demo-pump-cabinet")
    board = _labels_in_unit_sets(model, "demo-io-board")
    cabinet_texts = {label_text(model, lb) for lb in cabinet}
    board_relay = [label_text(model, lb) for lb in board if lb.slot == "tag"]
    assert "-X2" in cabinet_texts
    assert board_relay == ["-K1"] * 6  # coil and both contacts, in each of the two board sets
    for text in (*cabinet_texts, *(label_text(model, lb) for lb in board)):
        assert "+" not in text
        assert "=" not in text


def test_a_contacts_cross_reference_line_in_a_units_set_uses_the_same_short_form() -> None:
    """D12: a same-page cross-reference reads "2B", a contact image row "11-14 1B" (LD5's
    `position_text`: no prefix, no set number, no page for a partner on the label's own page)."""
    # UNDO: fransys_model/derive/drawing_text.py: `cross_reference_text` and `contact_image`
    #   treat a same-set partner as another set
    model = _system_model()
    board = _labels_in_unit_sets(model, "demo-io-board", kind=LabelKind.CROSS_REFERENCE)
    lines = [lb for lb in board if lb.slot == "tag"]
    images = [lb for lb in board if lb.slot == "contacts"]
    assert len(lines) == 4  # a line per contact, two board sets
    assert len(images) == 2
    assert all(re.fullmatch(r"\d+[A-Z]", label_text(model, lb)) for lb in lines)
    for image in images:
        header, *rows = label_text(model, image).split("\n")
        assert header == "NO | NC"
        assert len(rows) == 2
        assert all(re.fullmatch(r"\d+-\d+ \d+[A-Z] \| \d+-\d+ \d+[A-Z]", row) for row in rows)


def test_a_connector_pin_named_on_its_own_prints_dash_item_colon_port() -> None:
    """D12: a pin named on its own prints "-<item>:<port designation>", "-X1:1"."""
    # UNDO: fransys_model/derive/designation.py: `port_designation` drops the leading dash
    #   (model-0052's port-format order)
    model = _system_model()
    pins = _labels_in_unit_sets(model, "demo-io-board", slot="tag.pin.")
    assert len(pins) == 4  # two pins in each of the two board sets
    assert all(re.fullmatch(r"-\S+:\S+", label_text(model, lb)) for lb in pins)


def test_a_connector_designation_on_a_pin_row_lead_has_the_dash_of_every_item_tag() -> None:
    """D12 + designer ruling (GOLDEN-FIX 2 follow-up): `tag.conn` reads "-K1", never "K1": the
    `item_tag_text` of the connector's item, at top level and in a unit's own set alike."""
    # UNDO: fransys_model/derive/drawing_text.py: the `tag.conn` branch of `label_text` (top
    #   level) or of `unit_tag_text` (a unit's own set) returns `item_designation` again
    model = _system_model()
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    seen: dict[bool, set[str]] = {False: set(), True: set()}
    for lb in _labels(model, slot="tag.conn"):
        assert lb.function is not None
        unit = sets[pages[lb.page].drawing_set].unit
        item = functions(model)[lb.function].item
        text = label_text(model, lb)
        assert text == item_tag_text(model, item, unit=unit)
        assert text.startswith("-")
        seen[unit is not None].add(text)
    assert seen == {False: {"-K1"}, True: {"-WH1-P1", "-U1-X1"}}


def _three_phase(strip: str = "X01"):
    """Contactor Q1 feeds strip `strip` (L1, L2, L3, point 1) from its poles 2, 4, 6; the strip
    X1 feeds Q1's poles 1, 3, 5: two three-phase rows at the contactor's 32 G pole pitch."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1, g = d.location("C1", "Cabinet"), d.group("SUP", "Supply")
    q1 = d.item("DEMO-CTR-3P-24", tag="Q1", at=c1, group=g)
    feed_strip, out_strip = d.strip("X1", at=c1), d.strip(strip, at=c1)
    feed = [feed_strip.terminal("DEMO-TB-2.5", ph, group=g) for ph in ("L1", "L2", "L3")]
    out = [out_strip.terminal("DEMO-TB-2.5", ph, index=1, group=g) for ph in ("L1", "L2", "L3")]
    wire = d.wiring(colour="BK", gauge="2.5")
    main = q1.fn("main")
    for i in range(3):
        wire(feed[i].inner, main[str(2 * i + 1)])
        wire(main[str(2 * i + 2)], out[i].inner)
    return fr.build(parts, d.draft(), system_document())


def _units_strip(terminal_count: int, *, three_phase: bool):
    """A strip `X3` under the board unit's sole root (one that the authoring API cannot parent,
    so it is made from a part-less child item), the one case where the unit-relative and the
    top-level forms differ. Three-phase: contactor Q1 feeds its L1, L2, L3 at the pole pitch;
    else `terminal_count` plain terminals wired one to a relay coil pin each (one per row)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.unit("demo-io-board", revision=3, interface="2")
    u.revision(3, date="2026-01-01", text="First release", created="XX")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    strip_item = u.item(None, tag="X3", parent=board, group=grp)
    strip = fransys_author.Strip(u._design, strip_item.id, strip_item.key, u._unit)
    wire = u.wiring(colour="BU", gauge="0.5")
    if three_phase:
        q1 = u.item("DEMO-CTR-3P-24", name="q1", parent=board, group=grp)
        phases = [
            strip.terminal("DEMO-TB-2.5", ph, index=1, group=grp) for ph in ("L1", "L2", "L3")
        ]
        for i, terminal in enumerate(phases):
            wire(q1.fn("main")[str(2 * i + 2)], terminal.inner)
        return fr.build(parts, d.draft(), system_document()).model, phases
    relay = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    terminals = [strip.terminal("DEMO-TB-2.5", group=grp) for _ in range(terminal_count)]
    for terminal, pin in zip(terminals, ("A1", "A2"), strict=False):
        wire(terminal.inner, relay.fn("coil")[pin])
    return fr.build(parts, d.draft(), system_document()).model, terminals


def _terminal_tags(model, *, own_set: bool | None = None):
    """Every terminal TAG label of a strip terminal (a device's own terminal keeps its marking;
    a unit's black box is titled, not tagged, "outline_title")."""
    return [
        lb
        for lb in _labels(model, own_set=own_set)
        if lb.function is not None
        and lb.slot != "outline_title"
        and functions(model)[lb.function].kind is FunctionKind.TERMINAL
        and not is_device_terminal(model, lb.function)
    ]


def _derived_strip(model, lb) -> str:
    """The strip text derive gives a terminal's label: the unit's own short form in the unit's
    own set (`unit_tag_text`), else `strip_tag_text`."""
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[lb.page].drawing_set].unit
    if unit is not None and items(model)[functions(model)[lb.function].item].unit == unit:
        text = unit_tag_text(model, lb.function, "tag.strip", unit)
        assert text is not None  # the `tag.strip` slot always has a text
        return text
    return strip_tag_text(model, lb.function)


def _assert_terminal_texts_follow_d12(model) -> None:
    """Acceptance 7: every terminal text is the full form "-<strip>:<point>" except a point text
    in a run, which is short (no dash) and comes with the run's strip tag, once per run: a run is
    the point texts of one strip in one row of one page, and its strip tag says the derived
    strip text."""
    tags = _terminal_tags(model)
    assert tags
    stand_at = {(p.function, p.page): p.y for p in layout_of(model, SymbolPlacement).values()}

    def row(lb) -> tuple:
        return lb.page, stand_at[lb.function, lb.page], _derived_strip(model, lb)

    strips = [lb for lb in tags if lb.slot == "tag.strip"]
    points = [lb for lb in tags if lb.slot == "tag.point"]
    for strip in strips:
        assert label_text(model, strip) == _derived_strip(model, strip)
        assert sum(row(point) == row(strip) for point in points) >= 2  # a run: two or more
    for point in points:
        assert sum(row(strip) == row(point) for strip in strips) == 1
    for lb in tags:
        text = label_text(model, lb)
        if lb.slot == "tag.point":
            assert not text.startswith("-")
            assert text == run_point_text(model, lb.function)
        elif lb.slot != "tag.strip":
            assert re.match(r"-\S+:\S+", text)


@pytest.mark.parametrize(
    "build",
    [
        _system_model,
        lambda: _three_phase().model,
        lambda: _relay_pair(_crossed_feeds),
        lambda: _lamps_through_a_terminal(),  # noqa: PLW0108 -- the lambda defers the lookup: the function is defined below this decorator
        lambda: _units_strip(2, three_phase=False)[0],
        lambda: _units_strip(3, three_phase=True)[0],
    ],
    ids=["system", "three_phase", "chance_neighbours", "lone", "unit_lone", "unit_run"],
)
def test_every_terminal_text_is_the_full_form_except_a_point_text_in_a_run(build) -> None:
    """D12 / acceptance 7 over the worked example and the small fixtures."""
    # UNDO: fransys_model/derive/drawing_text.py: `run_point_text` returns
    #   `terminal_designation` (the full form in a run), or `label_text` gives a lone terminal
    #   its short point text
    _assert_terminal_texts_follow_d12(build())


def _check_top_level_designations_are_item_only(model) -> tuple[int, int]:
    """Every TAG label of a top-level set prints an item designation only: no "=" or "+" (D12,
    owner 2026-09-24, no top-level exception). Returns (labels checked, labels whose reference
    designation is longer than the item's), so a caller can tell the fixture is not vacuous."""
    labels = [lb for lb in _labels(model, own_set=False) if lb.function is not None]
    assert labels
    longer = 0
    for lb in labels:
        text = label_text(model, lb)
        record = functions(model)[lb.function]
        item = items(model)[record.item]
        assert "+" not in text
        assert "=" not in text
        longer += reference_designation(model, item.id) != f"-{item_designation(model, item.id)}"
        if lb.slot == "tag.strip":  # a run's strip, once
            assert text == strip_tag_text(model, lb.function)  # the derive function knows the item
        elif lb.slot == "tag.item":  # a mixed-kind row's item tag
            assert text == f"-{item_designation(model, item.id)}"
        elif lb.slot == "tag.conn":  # a pin row's one connector tag: dashed since designer ruling
            assert text == item_tag_text(model, item.id)  # (GOLDEN-FIX 2 follow-up; D12 "-Q11")
        elif lb.slot.startswith("tag.pin."):
            assert re.fullmatch(r"-[^+=\s]+:\S+", text)
        elif lb.slot == "tag" and record.kind is FunctionKind.TERMINAL:
            assert re.fullmatch(r"-[^+=\s]+:\S+", text)  # a lone terminal: "-X1:1"
        elif lb.slot == "tag":
            assert text == f"-{item_designation(model, item.id)}"
    return len(labels), longer


@pytest.mark.parametrize(
    "build",
    [
        _system_model,
        lambda: _three_phase().model,
        lambda: _relay_pair(_feed_relays),
        lambda: _lamps_through_a_terminal(),  # noqa: PLW0108 -- the lambda defers the lookup: the function is defined below this decorator
        lambda: _cabinet_model(),  # noqa: PLW0108 -- the lambda defers the lookup: the function is defined below this decorator
        lambda: _load(_ROOT_TESTS / "dd_stability_fixture.py").build(),
    ],
    ids=["system", "three_phase", "relay_pair", "lamps", "cabinet", "stability"],
)
def test_a_top_level_tag_is_the_item_designation_only(build) -> None:
    """D12 (amended, layout-0066) / acceptance 7: a top-level set prints "-Q1", never "=SUP+C1-Q1"
    or "+C1-Q1": the component tag, the run's strip tag and a pin or item view's tag alike."""
    # UNDO: fransys_model/derive/drawing_text.py: `tag_text` returns `reference_designation`
    #   again (or `strip_tag_text` does, or the `tag.item` branch of `label_text`)
    checked, longer = _check_top_level_designations_are_item_only(build())
    assert checked
    assert longer  # the fixture has located items: its reference designations are longer


def test_a_run_of_terminals_prints_its_strip_once_and_then_short_points() -> None:
    """D12: on each of the four pump-cabinet pages two terminals of one strip stand in one row:
    the strip once (left of the run) and a point text each."""
    # UNDO: fransys_model/derive/drawing_text.py: `run_point_text` returns the full form
    model = _system_model()
    points = _labels(model, slot="tag.point")
    strips = _labels(model, slot="tag.strip")
    assert len(points) == 8  # two terminals on each of four pump-cabinet pages
    assert len(strips) == 4  # one strip tag per run
    assert {label_text(model, lb) for lb in points} == {"1", "2"}
    assert all(label_text(model, lb) == _derived_strip(model, lb) for lb in strips)
    # two on the top-level pages and two in the units' own sets: all the item designation only
    # (D12 amended, layout-0066: no top-level exception)
    assert [label_text(model, lb) for lb in strips] == ["-X2"] * 4


def test_a_three_phase_row_prints_the_strip_once_and_l1_l2_l3_points() -> None:
    """D12: both rows of the three-phase feed print the strip and "L1:1", "L2:1", "L3:1"."""
    # UNDO: fransys_model/derive/drawing_text.py: `run_point_text` returns the full form
    model = _three_phase().model
    points = [label_text(model, lb) for lb in _labels(model, slot="tag.point")]
    strips = [label_text(model, lb) for lb in _labels(model, slot="tag.strip")]
    assert sorted(points) == ["L1:1"] * 2 + ["L2:1"] * 2 + ["L3:1"] * 2
    assert sorted(strips) == ["-X01", "-X1"]  # D12 amended (layout-0066): no "+C1" at top level


def test_two_terminals_of_a_strip_in_neighbouring_columns_keep_the_full_form() -> None:
    """D12: terminals that stand at the same height in two columns only by chance print the
    full form, "-X1:1", and no strip tag or point text at all."""
    # UNDO: fransys_layout/stages/tags.py: `terminal_row_tags` groups a strip's
    #   terminals of one page row instead of one column's row
    model = _relay_pair(_crossed_feeds)
    placed = {
        p.function: p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].kind is FunctionKind.TERMINAL
    }
    heights = [p.y for p in placed.values()]
    assert len(heights) == 4
    assert len(set(heights)) < len(heights)  # two terminals share a height ...
    assert len({p.x for p in placed.values()}) > 1  # ... in different columns
    assert not _labels(model, slot="tag.point")
    assert not _labels(model, slot="tag.strip")
    assert {label_text(model, lb) for lb in _terminal_tags(model)} == {
        "-X1:1",
        "-X1:2",
        "-X1:3",
        "-X1:4",
    }


def test_a_terminal_alone_in_its_row_keeps_the_full_form() -> None:
    """D12: a strip's one terminal, or one of two different strips in a row, is not a run."""
    # UNDO: fransys_model/derive/drawing_text.py: `label_text` gives a terminal's `tag` its
    #   `run_point_text`
    model = _lamps_through_a_terminal()
    (tag,) = _terminal_tags(model)
    assert tag.slot == "tag"
    assert label_text(model, tag) == "-X1:1"


def test_a_three_phase_row_of_short_points_collides_with_nothing() -> None:
    """D12 / acceptance 7: the -X01 row's three short points and its strip tag overlap no text,
    cross no wire, and every label is placed. (With the full form the row collides: below.)"""
    # UNDO: fransys_model/derive/drawing_text.py: `run_point_text` returns the full form
    for strip in ("X01", "X02", "X12"):
        codes = {f.code for f in _three_phase(strip).findings}
        assert codes.isdisjoint(_COLLISIONS), (strip, codes & _COLLISIONS)


def test_the_full_form_in_a_three_phase_row_overlaps_no_text_and_still_collides(
    monkeypatch,
) -> None:
    """Acceptance 7's can-fail, kept as a test: "-X01:L2:1" (34 G) is wider than the 32 G pole
    pitch. Since S18 (step 5 ADDENDUM 7) D3's placer steps a point text that meets its neighbour
    down to a free table step, so no two texts overlap (no TEXT_OVERLAP); but the rows still
    collide: a point text with no free step stands unplaced (LABEL_UNPLACED) and a wire crosses
    it (WIRE_OVER_LABEL), which the short points of the test above avoid."""
    # UNDO: stages/texts/candidates.py: `_ALONG = (0,)` (a tag at its home or its mirror only):
    #     the row's point texts overlap again (TEXT_OVERLAP)
    monkeypatch.setattr(
        drawing_text,
        "run_point_text",
        lambda model, function: terminal_designation(model, functions(model)[function].item),
    )
    built = _three_phase("X01")
    codes = {f.code for f in built.findings}
    assert "-X01:L2:1" in {label_text(built.model, lb) for lb in _terminal_tags(built.model)}
    assert "TEXT_OVERLAP" not in codes
    assert {"LABEL_UNPLACED", "WIRE_OVER_LABEL"} <= codes


_COLLISIONS = {
    "TEXT_OVERLAP",
    "LABEL_UNPLACED",
    "WIRE_OVER_LABEL",
    "ROUTE_FAILED",
    "CONNECTION_NOT_DRAWN",
}


def test_the_runs_texts_are_one_derive_function_each() -> None:
    """D12: `strip_tag_text` is the strip's text once ("-X01": the item designation, layout-0066),
    `run_point_text` a terminal's own "group:index" without its strip, and `point_text` is the
    second for a strip terminal."""
    # UNDO: fransys_model/derive/drawing_text.py: `run_point_text` returns
    #   `terminal_designation` (the full form)
    model = _three_phase().model
    out = [
        f.id
        for f in functions(model).values()
        if f.kind is FunctionKind.TERMINAL
        and terminal_designation(model, f.item).startswith("-X01:")
    ]
    assert sorted(run_point_text(model, f) for f in out) == ["L1:1", "L2:1", "L3:1"]
    assert {point_text(model, f) for f in out} == {"L1:1", "L2:1", "L3:1"}
    assert {strip_tag_text(model, f) for f in out} == {"-X01"}
    for f in out:
        full = terminal_designation(model, functions(model)[f].item)
        assert full == f"-X01:{run_point_text(model, f)}"


def test_a_component_tag_is_one_derive_function_at_top_level_and_in_a_unit() -> None:
    """D12 (amended, layout-0066): `item_tag_text` is "-" and the item designation, "-K1", with
    the aspects left out; a unit's own set's tag is the same function, unit-relative, and the
    run's strip tag and a function's tag call it."""
    # UNDO: fransys_model/derive/drawing_text.py: `item_tag_text` returns `reference_designation`
    model, terminals = _units_strip(2, three_phase=False)
    (unit,) = units(model)
    strip = next(i for i in items(model).values() if i.parent is not None).parent
    assert strip is not None
    board = items(model)[strip].parent
    assert board is not None
    assert item_tag_text(model, strip) == "-U1-X3"  # under the board's designation, top level
    assert item_tag_text(model, strip, unit=unit) == "-X3"  # the unit-relative form
    for terminal in terminals:
        function = terminal.function.id
        assert strip_tag_text(model, function) == item_tag_text(model, strip)
        assert unit_tag_text(model, function, "tag.strip", unit) == item_tag_text(
            model, strip, unit=unit
        )
    assert item_tag_text(model, board) == f"-{item_designation(model, board)}"
    top = _three_phase().model
    assert {
        item_tag_text(top, i.id) for i in items(top).values() if own_designation_or_none(top, i)
    } >= {"-Q1"}


def _mounted_device_terminal(*, in_unit: bool):
    """A relay and a terminal part used as a device (no terminal facet: a device's own terminal),
    both mounted on one item and wired together: the device terminal's parent is that item, the
    unit's board in a unit's own set, a rack (a part-less item) at top level, where a board's
    contents are not drawn."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    if in_unit:
        scope = d.unit("demo-io-board", revision=3, interface="2")
        scope.revision(3, date="2026-01-01", text="First release", created="XX")
        grp = scope.group("BRD", "I/O board")
        at = None
    else:
        grp = d.group("SUP", "Supply")
        scope = d
        at = d.location("C1", "Cabinet")
    board = scope.item("DEMO-PCB-IO" if in_unit else None, tag="A1", at=at, group=grp)
    relay = scope.item("DEMO-RLY-2CO-24", tag="K1", parent=board, at=at, group=grp)
    device = scope.item("DEMO-TB-2.5", tag="T9", parent=board, at=at, group=grp)
    scope.wiring(colour="BU", gauge="0.5")(
        device.fn("terminal")["internal"], relay.fn("coil")["A1"]
    )
    return fr.build(parts, d.draft(), system_document()).model, device.id, board.id


@pytest.mark.parametrize("in_unit", [False, True], ids=["top_level", "unit_set"])
def test_a_device_terminal_prints_the_devices_own_designation_not_its_boards(in_unit) -> None:
    """D12 (layout-0066): the device tag on the W of a device's own terminal is the device item's
    designation, also when the device is mounted on a board; only a real strip terminal's strip is
    its `item.parent`."""
    # UNDO: fransys_model/derive/drawing_text.py: `strip_tag_text` and `unit_tag_text`'s
    #   `tag.strip` branch take `item.parent or item.id` for a device terminal again
    model, device, board = _mounted_device_terminal(in_unit=in_unit)
    (unit,) = units(model) if in_unit else (None,)
    function = next(f.id for f in functions(model).values() if f.item == device)
    assert is_device_terminal(model, function)
    own = item_tag_text(model, device, unit=unit)
    assert own != item_tag_text(model, board, unit=unit)
    assert strip_tag_text(model, function) == item_tag_text(model, device)
    if in_unit:
        assert unit is not None
        assert unit_tag_text(model, function, "tag.strip", unit) == own
    (label,) = (
        lb for lb in _labels(model, own_set=in_unit, slot="tag.strip") if lb.function == function
    )
    assert label_text(model, label) == own


def test_a_lone_terminal_in_a_units_own_set_prints_the_unit_relative_full_form() -> None:
    """D12: in a unit's own set a lone strip terminal prints "-X3:1", the unit's short form that
    matches the short strip tag, not "-U1-X3:1" with the enclosing board's designation.

    The demo cabinet's strip has no parent item, so its two forms agree; here it sits under the
    board unit's sole root, the one case where they differ.
    """
    # UNDO: fransys_model/derive/drawing_text.py: `unit_tag_text` returns `None` for a
    #   non-device terminal's `tag` (the ordinary, top-level "-U1-X3:1" leaks into the set)
    model, terminals = _units_strip(2, three_phase=False)
    (unit,) = units(model)
    ids = [t.function.id for t in terminals]
    assert {terminal_designation(model, functions(model)[i].item) for i in ids} == {
        "-U1-X3:1",
        "-U1-X3:2",
    }
    assert {unit_tag_text(model, i, "tag", unit) for i in ids} == {"-X3:1", "-X3:2"}
    assert {label_text(model, lb) for lb in _terminal_tags(model, own_set=True)} == {
        "-X3:1",
        "-X3:2",
    }


def test_a_run_in_a_units_own_set_prints_the_short_strip_and_unit_independent_points() -> None:
    """D12: in a unit's own set a three-phase run prints the unit-relative strip "-X3" once and
    the same short points as at top level; the point text does not depend on the unit."""
    # UNDO: fransys_model/derive/drawing_text.py: `unit_tag_text` returns the unit-relative
    #   full form for a non-device terminal's `tag.point` ("-X3:L1:1")
    model, phases = _units_strip(3, three_phase=True)
    (unit,) = units(model)
    tags = _terminal_tags(model, own_set=True)
    points = [lb for lb in tags if lb.slot == "tag.point"]
    strips = [lb for lb in tags if lb.slot == "tag.strip"]
    assert sorted(label_text(model, lb) for lb in points) == ["L1:1", "L2:1", "L3:1"]
    assert [label_text(model, lb) for lb in strips] == ["-X3"]
    for terminal in phases:
        i = terminal.function.id
        assert unit_tag_text(model, i, "tag.point", unit) in (None, run_point_text(model, i))


# -- D15: page titles -----------------------------------------------------------------------


def test_a_page_of_a_units_own_set_is_titled_by_the_units_own_groups() -> None:
    """D15: a unit set page is titled by the unit's own groups ("I/O board").

    The worked example's unit pages hold no foreign group, so dropping the own-group filter is
    caught by the test below, not by this one; this one pins the own-group title itself."""
    # UNDO: fransys_model/derive/drawing_text.py: `page_title` returns "" or the unit name for
    #   every unit page (loses the own group's description)
    model = _system_model()
    expected = {"demo-io-board": "I/O board", "demo-pump-cabinet": "Field wiring"}
    seen = set()
    for page in layout_of(model, Page).values():
        unit = layout_of(model, DrawingSet)[page.drawing_set].unit
        if unit is not None:
            assert page_title(model, page) == expected[unit_release(model, unit).name]
            seen.add(unit_release(model, unit).name)
    assert seen == set(expected)


def _sibling_units(*, own_group_in_a: bool = False):
    """Two units, each with one relay standing in the one shared top-level group "Shared";
    with `own_group_in_a`, unit a has a second relay in a group "Mine" of its own."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    shared = d.group("SHR", "Shared")
    for number, name in enumerate(("a", "b"), 1):
        u = d.scope(name).unit("demo-pump-cabinet", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        loc = u.location(f"C{number}", "Cabinet")  # one location each: "+C1-K1" is not shared
        relay = u.item("DEMO-RLY-2CO-24", tag="K1", at=loc, group=shared)
        u.wiring(colour="BU", gauge="0.5")(relay.fn("coil")["A1"], relay.fn("coil")["A2"])
        if own_group_in_a and name == "a":
            mine = u.item("DEMO-RLY-2CO-24", tag="K2", at=loc, group=u.group("MINE", "Mine"))
            u.wiring(colour="BU", gauge="0.5")(mine.fn("coil")["A1"], mine.fn("coil")["A2"])
    result = fr.build(parts, d.draft(), system_document())
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    return result.model


def test_a_unit_page_shows_only_the_units_own_group_in_its_title_not_a_foreign_one() -> None:
    """D15: a page holding an own and a foreign group is titled "Mine", not "Mine, Shared"."""
    # UNDO: fransys_model/derive/drawing_text.py: `page_title` drops its `if group.group in own`
    #   filter (the title becomes "Mine, Shared")
    model = _sibling_units(own_group_in_a=True)
    nodes = aspect_nodes(model)
    sets = layout_of(model, DrawingSet)
    by_unit = {
        units(model)[unit].key: page
        for page in layout_of(model, Page).values()
        if (unit := sets[page.drawing_set].unit) is not None
    }
    page_a, page_b = by_unit[("a", "unit")], by_unit[("b", "unit")]
    assert [nodes[g.group].description for g in page_a.groups] == ["Mine", "Shared"]
    assert page_title(model, page_a) == "Mine"
    assert page_title(model, page_b) == "demo-pump-cabinet"


def test_a_unit_page_with_none_of_the_units_own_groups_takes_the_units_name() -> None:
    """D15: when every group on the page is another's, the page is titled by the unit's name."""
    # UNDO: fransys_model/derive/drawing_text.py: `page_title` drops its `or
    #   units(model)[unit].name` fallback (title "")
    model = _sibling_units()
    titles = [
        page_title(model, page)
        for page in layout_of(model, Page).values()
        if layout_of(model, DrawingSet)[page.drawing_set].unit is not None
    ]
    assert titles == ["demo-pump-cabinet"] * 2


def test_a_group_two_units_share_is_the_own_group_of_neither() -> None:
    """D11/D15: a group two units share is the own group of neither."""
    # UNDO: fransys_model/derive/designation.py: `own_nodes` ignores other units' items on a node
    model = _sibling_units()
    nodes = aspect_nodes(model)
    for unit in units(model):
        groups = {
            nodes[n].description
            for n in own_nodes(model, unit)
            if nodes[n].aspect is Aspect.FUNCTION
        }
        assert "Shared" not in groups
        assert {nodes[n].description for n in own_nodes(model, unit)} != set()


# -- D15: columns, jumpers, junctions -------------------------------------------------------


def _relay_pair(wire_up, *, bridge: tuple[int, int] | None = None):
    """The model of `_relay_built`."""
    return _relay_built(wire_up, bridge=bridge).model


def _relay_built(wire_up, *, bridge: tuple[int, int] | None = None):
    """Four terminals of one strip (group FLD "Field") and two relays (group RLY "Relays")."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    relays, field = d.group("RLY", "Relays"), d.group("FLD", "Field")
    strip = d.strip("X1", at=c1)
    terminals = [strip.terminal("DEMO-TB-2.5", group=field) for _ in range(4)]
    k1, k2 = (d.item("DEMO-RLY-2CO-24", tag=f"K{n}", at=c1, group=relays) for n in (1, 2))
    wire_up(d.wiring(colour="BU", gauge="0.5", label="W"), terminals, k1, k2)
    if bridge is not None:
        d.bridge(terminals[bridge[0]], terminals[bridge[1]])
    return fr.build(parts, d.draft(), system_document())


def _feed_relays(wire, t, k1, k2) -> None:
    wire(t[0].outer, k1.fn("coil")["A1"])
    wire(t[2].outer, k2.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], k2.fn("coil")["A2"])


def _lamps_through_a_terminal():
    """Lamps P1 and P2 (group LMP "Lamps") in series through one in-line terminal of group FLD."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    lamps, field = d.group("LMP", "Lamps"), d.group("FLD", "Field")
    terminal = d.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=field)
    p1 = d.item("DEMO-LAMP-24", tag="P1", at=c1, group=lamps)
    p2 = d.item("DEMO-LAMP-24", tag="P2", at=c1, group=lamps)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(p1.fn("lamp")["2"], terminal.outer)
    wire(terminal.inner, p2.fn("lamp")["1"])
    return fr.build(parts, d.draft(), system_document()).model


def test_a_terminal_in_another_group_does_not_give_its_column_that_group() -> None:
    """D15: a column's group comes from its device cells, never its terminals."""
    # UNDO: fransys_layout/stages/columns.py: `build_column` sets `devices = members`
    #   (terminal cells count in the common group; verified by probe: the page then lists no
    #   group at all)
    model = _lamps_through_a_terminal()
    (page,) = layout_of(model, Page).values()
    assert [aspect_nodes(model)[g.group].label for g in page.groups] == ["LMP"]
    placed = list(layout_of(model, SymbolPlacement).values())
    assert len(placed) == 3  # lamp, terminal, lamp: one column
    assert len({p.x for p in placed}) == 1


def test_a_jumper_is_no_schematic_connection_it_is_not_routed_and_has_no_wire_label() -> None:
    """D15: a jumper is not routed and carries no wire label."""
    # UNDO: fransys_layout/engines/schematic/read/reading.py: `connections` keeps
    #   `ConductorKind.JUMPER` conductors among the connections
    model = _relay_pair(_feed_relays, bridge=(0, 2))
    (jumper,) = [c.id for c in conductors(model).values() if c.kind is ConductorKind.JUMPER]
    routes = layout_of(model, Route).values()
    assert len(routes) == 3
    assert jumper not in {r.conductor for r in routes}
    assert not _labels(model, kind=LabelKind.WIRE)  # V8: no wire label stands on a page


def _grid_of_svg_dots(model, page):
    """The junction dots of `page`'s SVG in grid units, `content_x/y + g * module / 8`, inverted."""
    sheet = default_sheet_format()
    svg = render_pages(model)[f"{page.id.kind}:{page.id.value}"]
    dots = set()
    for cx, cy in re.findall(r'<circle class="junction" cx="([^"]+)" cy="([^"]+)"', svg):
        gx = (float(cx) - sheet.content_x_mm) * 8 / float(sheet.module_mm)
        gy = (float(cy) - sheet.content_y_mm) * 8 / float(sheet.module_mm)
        dots.add((round(gx), round(gy)))
    return dots


def _t_points(model, page):
    """Where three or more wire directions of one physical net leave a route vertex."""
    by_net: dict = {}
    for route in layout_of(model, Route).values():
        if route.page == page.id:
            points = [(p.x, p.y) for p in route.points]
            net = net_of(model, route.a)
            assert net is not None
            by_net.setdefault(net.ports, []).extend(itertools.pairwise(points))
    found = set()
    for segments in by_net.values():
        for vertex in {end for segment in segments for end in segment}:
            leaving = set()
            for (x1, y1), (x2, y2) in segments:
                x, y = vertex
                if x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2):
                    leaving |= {(0, 1)} if max(y1, y2) > y else set()
                    leaving |= {(0, -1)} if min(y1, y2) < y else set()
                if y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2):
                    leaving |= {(1, 0)} if max(x1, x2) > x else set()
                    leaving |= {(-1, 0)} if min(x1, x2) < x else set()
            if len(leaving) >= 3:
                found.add(vertex)
    return found


def _two_terminals_feed_two_relays(wire, t, k1, k2) -> None:
    wire(t[0].outer, k1.fn("coil")["A1"])
    wire(t[0].outer, k2.fn("coil")["A1"])
    wire(t[1].outer, k1.fn("coil")["A2"])
    wire(t[1].outer, k2.fn("coil")["A2"])


def _crossed_feeds(wire, t, k1, k2) -> None:
    wire(t[0].outer, k2.fn("coil")["A1"])
    wire(t[1].outer, k1.fn("coil")["A1"])
    wire(t[2].outer, k1.fn("coil")["A2"])
    wire(t[3].outer, k2.fn("coil")["A2"])


def test_a_junction_dot_stands_where_three_wire_directions_of_one_net_meet() -> None:
    """D15: junction dots stand only at the T points of the routed geometry."""
    # UNDO: fransys_render/_junctions.py: `_JUNCTION_THRESHOLD = 2` (a dot at every bend)
    model = _relay_pair(_two_terminals_feed_two_relays)
    (page,) = layout_of(model, Page).values()
    dots = _grid_of_svg_dots(model, page)
    assert dots  # the fixture has T points; a rule about nothing would pass too
    assert dots == _t_points(model, page)


def test_a_reference_at_a_joined_first_row_port_stays_inside_the_content_box() -> None:
    """S20 I4 Q1, M4: Room reserves the tier a joined port's reference starts at, so it fits.

    The fixture's first-row terminal port is joined to a side element, so its vertical
    reference's row starts one box length out; Room's N call must have reserved that.
    UNDO: stages/texts/stand.py `reserved_box`: `if True: return box` before the step.
    """
    built = _relay_built(_two_terminals_feed_two_relays)
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in built.findings}


def test_wires_that_only_run_side_by_side_get_no_junction_dot() -> None:
    """D15: four independent wires (each net of two ports) have routes and no dot."""
    # UNDO: fransys_render/_junctions.py: `_JUNCTION_THRESHOLD = 1` (a dot at every wire end)
    model = _relay_pair(_crossed_feeds)
    (page,) = layout_of(model, Page).values()
    assert len(layout_of(model, Route)) == 4
    assert _grid_of_svg_dots(model, page) == set()


# -- D15: straight crossings ----------------------------------------------------------------


def _cabinet_model():
    tests = _ROOT_TESTS.parent / "packages" / "fransys-layout" / "tests"
    sys.path.insert(0, str(tests))
    try:
        cabinet = _load(tests / "layout_cabinet.py")
    finally:
        sys.path.remove(str(tests))
    return lay_out_schematic(freeze(cabinet.build_cabinet(discovery=False)))[0]


def _crossings_and_overlaps(model):
    """`(interior crossings, touches, overlaps)` between routes of different physical nets."""
    routes = list(layout_of(model, Route).values())
    crossings, touches, overlaps = set(), set(), 0
    for i, first in enumerate(routes):
        for second in routes[i + 1 :]:
            if first.page != second.page or net_of(model, first.a) == net_of(model, second.a):
                continue
            for a1, a2 in itertools.pairwise(first.points):
                for b1, b2 in itertools.pairwise(second.points):
                    (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = (
                        (a1.x, a1.y, a2.x, a2.y),
                        (b1.x, b1.y, b2.x, b2.y),
                    )
                    a_vertical, b_vertical = ax1 == ax2, bx1 == bx2
                    if a_vertical == b_vertical:
                        same_line = (ax1 == bx1) if a_vertical else (ay1 == by1)
                        lo_a, hi_a = sorted((ay1, ay2) if a_vertical else (ax1, ax2))
                        lo_b, hi_b = sorted((by1, by2) if a_vertical else (bx1, bx2))
                        overlaps += same_line and min(hi_a, hi_b) >= max(lo_a, lo_b)
                        continue
                    vx, hy = (ax1, by1) if a_vertical else (bx1, ay1)
                    v = (a1, a2) if a_vertical else (b1, b2)
                    h = (b1, b2) if a_vertical else (a1, a2)
                    on_v = min(v[0].y, v[1].y) <= hy <= max(v[0].y, v[1].y)
                    on_h = min(h[0].x, h[1].x) <= vx <= max(h[0].x, h[1].x)
                    if on_v and on_h:
                        inside = min(v[0].y, v[1].y) < hy < max(v[0].y, v[1].y) and (
                            min(h[0].x, h[1].x) < vx < max(h[0].x, h[1].x)
                        )
                        (crossings if inside else touches).add((first.page, vx, hy))
    return crossings, touches, overlaps


def test_routes_of_different_nets_only_cross_straight_and_share_no_track(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D15: crossings are straight and no two nets share a track.

    The fixture is the chained cabinet (`discovery=False`) with `attach_replicas` off: its three
    crossings came from the -X2:1 replica standing apart, and V4 now draws that replica over its
    pin, which leaves the cabinet none. The discovery cabinet has none since S20 M12 turned its
    same-side stars into wires. No
    single-line undo is known to fail this: the router avoids sharing a track on cost alone.
    It fails once both rules go (axes empty AND the profile's `route_crossing_penalty` 0: 2
    touches, 1 shared track). D15's other tests carry the can-fail load for the rest of the
    rule."""
    # UNDO: (two edits) fransys_layout/stages/route.py: drop the `axes` of foreign nets in
    #   `_draw` (`if foreign:` -> False) AND set `crossing_penalty=0` in its `Field`
    monkeypatch.setattr(engine, "attach_replicas", lambda columns, *_: columns)
    model = _cabinet_model()
    crossings, touches, overlaps = _crossings_and_overlaps(model)
    assert crossings  # the fixture does cross; a rule about nothing would pass too
    assert touches == set()
    assert overlaps == 0
    for page_id in {page for page, _, _ in crossings}:
        page = layout_of(model, Page)[page_id]
        assert not {(x, y) for p, x, y in crossings if p == page_id} & _grid_of_svg_dots(
            model, page
        )
