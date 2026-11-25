"""Field case: a document of two drawing sets, a cabinet and a board inside it, keeps the membership rows of both.
The bug: writing a set removed every membership row, not only its own, so the other sets were lost (designer R522).
Fixed by el-0068, a set replaces its own membership rows and leaves the others'."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _field_designs import fc_design, fc_unit
from _model_build_cover import _COVER, unit_document
from fransys.colours import BK, BU

from fransys_model.derive import document_drawing_sets
from fransys_model.layout import DrawingSet, Membership, layout_of
from fransys_model.vocab.tables import documents


class _Io(NamedTuple):
    X1: fr.Device


class _Open(NamedTuple):
    pass


@fc_unit("demo-board", title="Relay board")
def _board(u: Any) -> Any:
    pcb = u.device("A1", "DEMO-PCB-IO")
    with u.function("F1", "Board circuit"):
        x = u.device("X1", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
        lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.series(x[1], lamp["1"], wire=(BK, 0.5))
    u.series(x[2], lamp["2"], wire=(BU, 0.5))
    return _Io(X1=x)


@fc_unit("demo-cab", title="Cabinet")
def _cabinet(u: Any) -> _Open:
    board = u.add(_board, "U1")
    lamp = u.device("H1", "DEMO-LAMP-24")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X1[1], lamp["1"])
    cable.core(2, board.X1[2], lamp["2"])
    return _Open()


@pytest.mark.rule("OVERVIEW-MEMBERSHIP")
def test_every_drawing_set_keeps_its_membership_rows() -> None:
    d = fr.design("demo_parts")
    d.add(_cabinet, "C1", place=None)
    model = fr.build(d, unit_document("demo-cab")).model
    sets = layout_of(model, DrawingSet)
    kept = {m.key[3] for m in layout_of(model, Membership).values()}
    assert len(sets) >= 2
    assert kept == {str(s.number) for s in sets.values()}


# TEXT_HIDES_TEXT: a falling stock of this file's builds, KI-1133 (R2647, TEXT-WIRE P0).


def _system_of_two_cabinets() -> fr.BuildResult:
    d = fc_design("Two cabinets")
    d.add(_cabinet, "C1", place=None)
    d.add(_cabinet, "C2", place=None)
    result = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=_COVER))
    expect_codes(result, "UNPRINTED_SET")
    return result


@pytest.mark.rule("UNIT-SCOPE")
def test_a_system_document_of_two_identical_units_holds_no_set_inside_a_unit() -> None:
    """SYSTEM-UNIT-SETS: a unit set fell back to the root document, so the system PDF printed every unit's inside."""
    model = _system_of_two_cabinets().model
    (system,) = documents(model)
    assert layout_of(model, DrawingSet)
    assert [s for s in document_drawing_sets(model, system) if s.unit is not None] == []


@pytest.mark.rule("UNIT-SCOPE")
def test_each_unit_set_that_no_document_prints_is_an_error_naming_the_fix() -> None:
    result = _system_of_two_cabinets()
    unit_sets = [s for s in layout_of(result.model, DrawingSet).values() if s.unit is not None]
    errors = [f for f in result.findings if f.code == "UNPRINTED_SET"]
    assert len(errors) == len(unit_sets) > 0
    assert all("Add a document for" in f.message for f in errors)
