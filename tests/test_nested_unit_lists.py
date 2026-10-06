"""A nested unit's lists print an end outside the unit as an EMPTY cell (units spec U2, 2026-09-24).

Owner rule: "every drawing of a specific unit/part only knows whats going on below them in the
system ... the pcb drawing does not know what cabinet it will get placed into." For a NESTED
unit (`Unit.parent is not None`) the connector list's mate and pin-mate columns, the terminal
list's two ends columns and the wire-label list's two end columns print an end whose item is
outside the unit's subtree (`unit=None` included) as `""`. A top-level unit and `unit=None`
are unchanged. Decision model-0056.
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from fransys_pdf import _lists

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by
# name: `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _PROJECT, _system_design

from fransys_model.derive import (
    allocate_plc,
    boards,
    cell_text,
    connector_rows,
    list_context,
    plc_channel_rows,
    terminal_rows,
    terminal_strips,
    unit_release,
    wire_rows,
)
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import Id, SchemaError, freeze, merge
from fransys_model.vocab.tables import (
    aspect_nodes,
    documents,
    items,
)
from fransys_model.vocab.tables import units as units_table


def _unit_id(model, *, name, prefix):
    return next(
        unit_id
        for unit_id, unit in units_table(model).items()
        if unit_release(model, unit_id).name == name and unit.key[0] == prefix
    )


@pytest.fixture(scope="module")
def worked():
    """The units worked example with a document per unit: `(result, pump1 cabinet, pump1 board)`."""
    covers = Path(tempfile.mkdtemp())
    for name in ("cabinet", "board"):
        (covers / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    draft = d.draft()
    probe = fr.build(parts, draft).model
    cabinet = _unit_id(probe, name="demo-pump-cabinet", prefix="pump1")
    board = _unit_id(probe, name="demo-io-board", prefix="pump1")
    result = fr.build(
        parts,
        draft,
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=covers / "cabinet.md"),
        fr.document(fr.DocumentPreset.PCB_SCHEMATIC, board, cover=covers / "board.md"),
    )
    return result, cabinet, board


def _document_of(model, unit):
    return next(record for record in documents(model).values() if record.unit == unit)


def _board_item(model, unit):
    (board_item,) = (item for item in boards(model) if items(model)[item].unit == unit)
    return board_item


# -- 1. derive: the connector row ------------------------------------------------------------


def test_a_nested_units_connector_row_prints_no_mate_but_keeps_the_mate_ids(worked):
    result, _cabinet, board = worked
    model = result.model
    (row,) = connector_rows(model, _board_item(model, board), unit=board)
    assert row.designation == "-X1"
    assert row.mate is not None
    assert row.mate_designation is None
    assert [pin.marking for pin in row.pins] == ["1", "2"]
    assert all(pin.mate_port is not None for pin in row.pins)
    assert all(pin.mate_port_designation is None for pin in row.pins)


def test_the_same_connector_row_without_a_unit_still_prints_its_mate(worked):
    result, _cabinet, board = worked
    model = result.model
    (row,) = connector_rows(model, _board_item(model, board))
    assert row.mate_designation is not None
    assert row.mate_designation.endswith("-WH1-P1")
    assert all(pin.mate_port_designation is not None for pin in row.pins)


# -- 2. PDF: the connector list page -----------------------------------------------------------


def test_a_nested_units_connector_list_page_draws_no_mate_column(worked):
    result, _cabinet, board = worked
    page = _lists.connector_list_page(result.model, _document_of(result.model, board))
    assert "-X1" in page
    assert 'text("1")' in page
    assert 'text("2")' in page
    assert "WH1-P1" not in page
    assert "Mate designation" not in page
    assert "Mate port designation" not in page


# -- 3. CSV: the connector list ----------------------------------------------------------------


def test_a_nested_units_connector_csv_keeps_its_columns_with_the_mate_cells_empty(worked, tmp_path):
    result, _cabinet, board = worked
    written = fr.write(result, tmp_path, unit=board)
    # the board is its own unit's root, so its list is the bare kind name (UNIT-ID I5)
    (csv_path,) = (path for path in written if path.name.endswith("connectors.csv"))
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("designation,style,pincount,gender,mate_designation,")
    assert "-X1,header-2p,2,male,,1,," in lines
    assert "-X1,header-2p,2,male,,2,," in lines
    assert "WH1-P1" not in "\n".join(lines)


# -- 4. terminal outside ends and the wire list --------------------------------------------------


def _nested_strip_model():
    """A nested unit `inner` (a strip `-X5` and a plug `-P1`) inside the unit `outer`.

    `-X5:1` internal side: one wire to `outer`'s plug `-P9` (outside `inner`). `-X5:1` external
    side: a wire to `inner`'s own `-P1` (inside) and a wire to a top-level motor `-M1` (in no
    unit). One core of `inner`'s own cable runs from `-X5:2` to `-P9`; `outer`'s own cable has
    one core, `-P9:2` to the motor `-M1`.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    outer = d.scope("pump1", at=er).unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = outer.location("C1", "Cabinet")
    outer_grp = outer.group("OUT", "Outer")
    p9 = outer.item("DEMO-CONN-2P", tag="P9", at=cab, group=outer_grp)
    inner = outer.scope("io", at=cab).unit("inner", revision=1, interface="1")
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    inner_grp = inner.group("IN", "Inner")
    strip = inner.strip("X5", at=cab)
    terminals = [strip.terminal("DEMO-TB-2.5", group=inner_grp) for _ in range(2)]
    p1 = inner.item("DEMO-CONN-2P", tag="P1", at=cab, group=inner_grp)
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=fld, group=fld_grp)
    wire = inner.wiring(colour="BU", gauge="0.5")
    wire(terminals[0].inner, p9["1"])
    wire(terminals[0].outer, p1["1"])
    wire(terminals[0].outer, motor["U"])
    cable = inner.cable("DEMO-CBL-4G1.5", name="w", at=cab)
    cable.core(1, terminals[1].inner, p9["2"])
    outer_cable = outer.cable("DEMO-CBL-4G1.5", name="wo", at=cab)
    outer_cable.core(1, p9["2"], motor["V"])
    model, _findings = number_pass(freeze(merge(parts, d.draft())))
    return model, _unit_id(model, name="inner", prefix="pump1"), strip.id


@pytest.fixture(scope="module")
def nested():
    return _nested_strip_model()


def test_a_nested_units_terminal_row_prints_an_outside_end_as_empty_and_keeps_the_length(nested):
    model, inner, strip = nested
    first, _second = terminal_rows(model, strip, unit=inner, context=list_context(model, strip))
    assert len(first.internal_ends) == len(first.internal) == 1
    assert first.internal_ends == ("",)  # `-P9:1`, of the parent unit
    assert len(first.external_ends) == len(first.external) == 2
    assert sorted(first.external_ends) == ["", "-P1:1"]  # the motor is in no unit: outside too


def test_a_nested_units_terminal_cell_never_prints_a_dangling_separator(nested):
    model, inner, strip = nested
    rows = terminal_rows(model, strip, unit=inner, context=list_context(model, strip))
    table = _lists._terminal_table(model, rows)
    assert 'text("-P1:1")' in table
    assert "; " not in table
    assert cell_text(rows[0].external_ends) == "-P1:1"
    assert cell_text(rows[0].internal_ends) == ""


def test_the_same_strip_read_without_a_unit_prints_every_end(nested):
    model, _inner, strip = nested
    first, _second = terminal_rows(model, strip)
    assert len(first.internal_ends) == 1
    assert len(first.external_ends) == 2
    assert all(first.internal_ends)
    assert all(first.external_ends)


def test_a_nested_units_wire_list_holds_only_its_own_wire_with_both_ends_printed(nested):
    model, inner, _strip = nested
    (row,) = wire_rows(model, unit=inner)
    assert (row.from_, row.to) == ("-X5:1", "-P1:1")
    assert row.label == "-X5:1 -P1:1"


def test_the_same_wire_list_read_without_a_unit_prints_every_wire_in_full(nested):
    model, _inner, _strip = nested
    rows = wire_rows(model)
    assert _flat_ends(rows) == [
        "+ER+C1-P1:1",
        "+ER+C1-P9:1",
        "+ER+C1-X5:1",
        "+ER+C1-X5:1",
        "+ER+C1-X5:1",
        "+FLD-M1:U",
    ]


# -- 5. unchanged: a top-level unit and `unit=None` -------------------------------------------


def test_a_top_level_units_terminal_list_still_prints_its_outside_ends(worked):
    result, cabinet, _board = worked
    model = result.model
    (strip,) = (s for s in terminal_strips(model) if items(model)[s].unit == cabinet)
    rows = terminal_rows(model, strip, unit=cabinet, context=list_context(model, strip))
    side_b = [end for row in rows for end in row.external_ends]
    assert "+FLD-M1:U" in side_b
    assert "+FLD-K1:1" in side_b


def test_a_terminal_list_without_a_unit_still_prints_its_outside_ends(worked):
    result, cabinet, _board = worked
    model = result.model
    (strip,) = (s for s in terminal_strips(model) if items(model)[s].unit == cabinet)
    rows = terminal_rows(model, strip, context=list_context(model, strip))
    side_b = [end for row in rows for end in row.external_ends]
    assert "+FLD-M1:U" in side_b
    assert "+FLD-K1:1" in side_b
    assert all(end for end in side_b)


# -- 6. a unit document's lists print against the unit's own placement location -----------------


def test_unit_location_is_the_location_of_the_units_root_items(worked):
    from fransys_model.derive.designation import unit_location

    result, cabinet, board = worked
    model = result.model
    nodes = aspect_nodes(model)
    for unit in (cabinet, board):
        location = unit_location(model, unit)
        assert location is not None
        assert nodes[location].label == "C1"


def _flat_ends(rows):
    return sorted(end for row in rows for end in (row.from_, row.to))


def test_a_nested_units_wire_labels_read_short_against_its_placement_location(worked, tmp_path):
    result, _cabinet, board = worked
    short = ["-K1:A1", "-K1:A2", "-X1:1", "-X1:2"]
    assert _flat_ends(wire_rows(result.model, unit=board)) == short
    written = fr.write(result, tmp_path, unit=board)
    (csv_path,) = (path for path in written if path.name.endswith("wires.csv"))
    cells = [line.split(",") for line in csv_path.read_text(encoding="utf-8").splitlines()[1:]]
    assert sorted(end for cell in cells for end in cell[:2]) == short


def test_a_top_level_units_wire_list_reads_short_inside_and_leaves_out_a_wire_to_no_unit(nested):
    model, _inner, _strip = nested
    outer = _unit_id(model, name="outer", prefix="pump1")
    # the wire to the motor, which is in no unit, is not `outer`'s
    assert _flat_ends(wire_rows(model, unit=outer)) == ["-P9:1", "-X5:1"]  # both inside `outer`


def test_a_units_list_ignores_the_callers_context(nested):
    model, _inner, _strip = nested
    outer = _unit_id(model, name="outer", prefix="pump1")
    field = next(node for node, record in aspect_nodes(model).items() if record.label == "FLD")
    assert _flat_ends(wire_rows(model, unit=outer, context=field)) == _flat_ends(
        wire_rows(model, unit=outer)
    )
    assert "-P9:1" in _flat_ends(wire_rows(model, unit=outer, context=field))


def test_a_list_without_a_unit_still_prints_the_full_path(nested):
    model, _inner, _strip = nested
    (row,) = (r for r in wire_rows(model) if r.to == "+FLD-M1:U" or r.from_ == "+FLD-M1:U")
    assert _flat_ends([row]) == ["+ER+C1-X5:1", "+FLD-M1:U"]


# -- 7. the PLC list ---------------------------------------------------------------------------


def _plc_model(*, nested_host):
    """A DO module `-A1`, a relay served from it inside its unit and one in no unit, at `FLD`.

    `nested_host`: the module, its relay `kin` and their strip sit in the nested unit `plcu` of
    the top-level unit `cab` (placement location `C1`); else in `cab` itself. `kout` and its own
    strip belong to no unit, at the location `FLD`. Channel 1 of `-A1` is wired to the host's
    strip terminal, channel 2 to `kout`'s strip terminal (`wired_to` reads the wiring, not the
    binding; which relay a channel serves is the allocator's, so the tests key rows by channel).
    `kout` is in no unit, yet allocation binds it to channel 2 because it is wired there
    (PLC-WIRED, model-0083); the fixture no longer binds it by hand.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    cab = d.scope("s", at=er).unit("cab", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c = cab.location("C1", "Cabinet")
    if nested_host:
        host, at = cab.scope("p", at=c).unit("plcu", revision=1, interface="1"), None
        host.revision(1, date="2026-01-01", text="First release", created="XX")
    else:
        host, at = cab, c
    grp = host.group("G", "Plc")
    module = host.item("DEMO-PLC-DO-2", tag="A1", at=at, group=grp)
    kin = host.item("DEMO-RLY-2CO-24", name="kin", at=at, group=grp)
    term_in = host.strip("X1", at=at).terminal("DEMO-TB-2.5", group=grp)
    host.wiring(colour="BU", gauge="0.5")(term_in.inner, kin["A1"])
    host.wiring(colour="BU", gauge="0.5")(module.fn("do_1")["1"], term_in.outer)
    kin.fn("coil").plc("do", "IN")
    kout = d.item("DEMO-RLY-2CO-24", name="kout", at=fld, group=fld_grp)
    term_out = d.strip("X9", at=fld).terminal("DEMO-TB-2.5", group=fld_grp)
    d.wiring(colour="BU", gauge="0.5")(term_out.inner, kout["A1"])
    d.wiring(colour="BU", gauge="0.5")(module.fn("do_2")["2"], term_out.outer)
    kout.fn("coil").plc("do", "OUT")
    model, _ = number_pass(freeze(merge(parts, d.draft())))
    model, _ = allocate_plc(model)
    unit = _unit_id(model, name="plcu" if nested_host else "cab", prefix="s")
    return model, unit


def _plc_rows(model, unit):
    """The unit's PLC rows by channel designation: `{"-A1:1": row, "-A1:2": row}`."""
    return {row.channel_designation: row for row in plc_channel_rows(model, unit=unit)}


def test_a_nested_units_plc_row_leaves_an_outside_end_and_an_outside_device_empty():
    model, plcu = _plc_model(nested_host=True)
    rows = _plc_rows(model, plcu)
    assert rows["-A1:1"].signal is not None
    assert rows["-A1:1"].wired_to == "-X1:1"  # the unit's own strip, short
    outside = rows["-A1:2"]  # wired to `kout`'s strip, in no unit
    assert outside.signal is not None
    assert outside.wired_to is None
    # `kout`, in no unit, is bound to one of the channels (`field_device`) but never printed
    assert all(row.field_device is not None for row in rows.values())
    assert sorted(row.field_device_designation is None for row in rows.values()) == [False, True]


def test_a_top_level_units_plc_row_keeps_its_outside_end_and_prefixes_its_location():
    model, cab = _plc_model(nested_host=False)
    rows = _plc_rows(model, cab)
    assert rows["-A1:1"].wired_to == "-X1:1"  # inside `cab`'s own placement location `C1`
    assert rows["-A1:2"].wired_to == "+FLD-X9:1"  # `kout`'s strip, outside it
    assert all(row.field_device_designation is not None for row in rows.values())


def test_a_plc_list_without_a_unit_prints_the_full_path():
    model, _cab = _plc_model(nested_host=False)
    rows = _plc_rows(model, None)
    assert rows["-A1:1"].wired_to == "+ER+C1-X1:1"
    assert rows["-A1:2"].wired_to == "+FLD-X9:1"


def test_a_list_for_an_unknown_unit_raises_a_schema_error(worked, nested):
    from fransys_model.derive.designation import end_outside_nested_unit

    result, _cabinet, board = worked
    model, _inner, strip = nested
    unknown = Id(kind="unit", value="no-such-unit")
    with pytest.raises(SchemaError):
        terminal_rows(model, strip, unit=unknown)
    with pytest.raises(SchemaError):
        connector_rows(result.model, _board_item(result.model, board), unit=unknown)
    # the helper itself, reached first by an end no other lookup has refused yet
    with pytest.raises(SchemaError):
        end_outside_nested_unit(model, strip, unknown)
