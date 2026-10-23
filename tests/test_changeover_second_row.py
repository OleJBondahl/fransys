"""PORT-LINE: a changeover's second-throw terminals stand in one row (R467 Q27).

The fixture is the field case `field_cases/test_changeover_throws_to_two_strips.py` inside its
unit: poles 3 and 4 of a changeover, each throw wired to its own terminal of a field strip
that stands at another location than the relay. Layout-0090's two rows are retired: the
neighbour stands on its port's side and line, so both throws stand in one row.

A second fixture gives the strips names so long that the terminals' labels are wider than the
16-unit pitch of a row (the "unless their labels collide" half of the row): whatever the layout
does there, no two labels of the pole's terminals overlap.

Can-fail probes: a patch standing the make throw in a second row fails the one-row test; a patch
that stacks the two terminals' labels in one box fails the labels-collide test; a patch swapping
the two poles' columns fails the pole-order test.
"""

import importlib.util
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BK

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`, and
# ty cannot resolve a `sys.path` insert; the field case's own build is loaded from its file.
_FIELD_CASE = (
    Path(__file__).resolve().parent / "field_cases" / "test_changeover_throws_to_two_strips.py"
)
_spec = importlib.util.spec_from_file_location("_changeover_field_case", _FIELD_CASE)
assert _spec is not None
assert _spec.loader is not None
_field_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_field_case)

_POLES = (3, 4)
_LONG = ("X01A_VERY_LONG_STRIP_NAME", "X02B_VERY_LONG_STRIP_NAME")


def _long_label_circuit(d: fr.Design):
    """The field case's circuit with strip names whose terminal labels outrun a row's pitch."""
    d.location("CAB", "Cabinet")
    d.location("FIELD", "Field strips")
    make_strip = d.terminal_strip(_LONG[0], _field_case._TERMINAL, place="FIELD")
    break_strip = d.terminal_strip(_LONG[1], _field_case._TERMINAL, place="FIELD")
    relay = d.device("K1", _field_case._CHANGEOVER, place="CAB")
    for pole in _POLES:
        throws = getattr(relay, f"co_{pole}")
        make = make_strip.run(f"RUN{pole}", 1)[1]
        brk = break_strip.run(f"RUN{pole}", 1)[1]
        d.detail.wire(brk, throws[f"{pole}2"], wire=(BK, 1.5))
        d.detail.wire(make, throws[f"{pole}4"], wire=(BK, 1.5))
    feed = d.terminal_strip("X03", _field_case._TERMINAL, place="CAB")
    d.detail.wire(feed[1], relay.coil["A1"], wire=(BK, 0.75))
    d.detail.wire(feed[2], relay.coil["A2"], wire=(BK, 0.75))
    return _field_case._Open()


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    """The field case's build inside its unit, shared by the module's tests."""
    return _field_case._build(tmp_path_factory.mktemp("second_row"), in_unit=True).model


@pytest.fixture(scope="module")
def long_model(tmp_path_factory):
    """The same changeover wired to strips with long names, inside a unit, built once."""
    unit = fr.unit(
        "unit", revision=1, interface_version=1, date="2026-09-26", text="First issue", by="XX"
    )(_long_label_circuit)
    d = fr.design("demo_parts")
    d.add(unit, "UNIT")
    cover = tmp_path_factory.mktemp("long_labels") / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "unit", cover=cover)
    return fr.build(d, document).model


def _pole(model, pole: int):
    """The (page, symbol) of the changeover contact of pole `pole`; its common is `<pole>1`."""
    (found,) = [
        (page, s)
        for page, drawing in drawn_pages(model).items()
        for s in drawing.symbols
        if s.key == "change-over-contact" and dict(s.slots).get("marking.com") == f"{pole}1"
    ]
    return found


def _rows_under(model, pole: int) -> list:
    """The terminals in the pole's column on its page, one list per row, top row first."""
    page, head = _pole(model, pole)
    column = [
        s
        for s in drawn_pages(model)[page].symbols
        if s.key == "terminal" and abs(s.x - head.x) <= 16
    ]
    return [[s for s in column if s.y == y] for y in sorted({s.y for s in column})]


@pytest.mark.rule("PORT-LINE")
@pytest.mark.parametrize("pole", _POLES)
def test_second_throw_terminals_stand_in_one_row_under_their_pole(model, pole) -> None:
    """PORT-LINE: "Second-throw terminals stand in one row unless their labels collide." (R467 Q27)

    The pole's break and make terminals share one row below the pole, with no marker on the page.
    """
    page, head = _pole(model, pole)
    rows = _rows_under(model, pole)
    assert len(rows) == 1  # one row holds the break and the make terminal
    assert len(rows[0]) == 2
    assert all(s.y > head.y for s in rows[0])
    assert not drawn_pages(model)[page].markers


@pytest.mark.rule("PORT-LINE")
def test_poles_stand_in_pole_order_with_both_throws_in_one_row(model) -> None:
    """PORT-LINE: pole 3's terminals stand left of pole 4's, all four on one row (R467 Q27)."""
    rows = [_rows_under(model, pole)[0] for pole in _POLES]
    assert len({s.y for row in rows for s in row}) == 1
    assert max(s.x for s in rows[0]) < min(s.x for s in rows[1])
    assert _pole(model, 3)[1].x < _pole(model, 4)[1].x


@pytest.mark.rule("PORT-LINE")
@pytest.mark.parametrize("pole", _POLES)
def test_labels_that_collide_never_overlap_under_a_pole(long_model, pole) -> None:
    """PORT-LINE: "unless their labels collide": long labels of one pole's terminals stay apart.

    The layout may keep one row (stacking the texts) or split it; either way no two of the
    pole's terminal labels share any area, and no marker stands in for a throw.
    """
    page, _ = _pole(long_model, pole)
    drawing = drawn_pages(long_model)[page]
    labels = [t.box for t in drawing.texts if f"RUN{pole}" in t.text]
    assert len(labels) == 2
    assert all(wide.w > 16 for wide in labels)  # wider than a row's pitch: they could collide
    a, b = labels
    assert a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
    assert not drawing.markers
