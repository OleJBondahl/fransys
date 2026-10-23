"""A symbol's footprint: measured tag, a coil's contact table, a strip row."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

from fransys_model.derive.contact_rows import table_geometry
from fransys_model.derive.footprints import footprints
from fransys_model.derive.rows_footprints import Extent
from fransys_model.derive.tag_text import tag_text
from fransys_model.derive.text_width import text_width
from fransys_model.layout import Side
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function


def _e(x: int, y: int, width: int, height: int) -> Extent:
    return Extent(x=x, y=y, width=width, height=height)


_LONG = "QLONGTAGGEDDESIGNATION"
_STEP, _PAD, _HEIGHT = 8, 2, 8

# real library geometry (terminal, circuit-breaker, coil), printed from symbol_geometry
_TERMINAL = (_e(-8, -8, 16, 16), {"tag": _e(4, -30, 48, 8)}, Side.E)
_BREAKER = (
    _e(-8, -16, 44, 32),
    {"tag": _e(-60, -4, 48, 8), "marking.top": _e(-8, -22, 54, 6)},
    Side.W,
)
_COIL = (_e(-4, -16, 4, 32), {"tag": _e(-56, -4, 48, 8), "marking.a1": _e(0, -16, 14, 8)}, Side.W)


@pytest.fixture(scope="module")
def model() -> Model:
    """A terminal, a short and a long breaker and a relay with its coil and contacts."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("F", "Func"):
        d.device("Q1", "DEMO-MCB-2P", place="L0")
        d.device(_LONG, "DEMO-MCB-2P", place="L0")
        d.device("X1", "DEMO-TB-2.5", place="L0")
        d.device("K1", "DEMO-RLY-2CO-24", place="L0")
        d.device("A1", "DEMO-RELAY-MOD-2", place="L0")
    return fr.build(d).model


def _function(model: Model, tag: str, kind: FunctionKind) -> Id[Function]:
    return next(
        f for f, r in functions(model).items() if r.kind is kind and tag_text(model, f) == tag
    )


def _foot(model: Model, function: Id[Function], geometry: tuple):
    body, slots, side = geometry
    return footprints(
        model, function, body=body, slots=slots, tag_side=side,
        text_height=_HEIGHT, step=_STEP, pad=_PAD,
    )  # fmt: skip


def test_a_terminal_shrinks_to_its_body_in_a_strip_row_and_is_the_library_keepout_alone(
    model: Model,
) -> None:
    terminal = _function(model, "-X1:internal", FunctionKind.TERMINAL)
    assert text_width("-X1:internal", height=_HEIGHT) < 48  # a short designation: slot unchanged
    foot = _foot(model, terminal, _TERMINAL)
    assert foot.in_strip_row == _e(-8, -8, 16, 16)
    assert foot.standalone == _e(-8, -30, 60, 38)  # the library keep-out
    assert foot.standalone.width > foot.in_strip_row.width


def test_a_long_designation_widens_the_tag_slot_toward_its_side(model: Model) -> None:
    short = _foot(model, _function(model, "-Q1", FunctionKind.PROTECTION), _BREAKER)
    tag = f"-{_LONG}"
    wide = text_width(tag, height=_HEIGHT)
    assert wide > 48
    long = _foot(model, _function(model, tag, FunctionKind.PROTECTION), _BREAKER)
    assert short.standalone == _e(-60, -22, 106, 38)  # the library keep-out
    assert long.standalone.x == -12 - wide  # W: the slot's right edge stays at -12
    assert long.standalone.width == short.standalone.width + wide - 48
    east = _foot(model, _function(model, tag, FunctionKind.PROTECTION), _TERMINAL)
    assert east.standalone.x == -8
    assert east.standalone.width == 4 + wide + 8  # E: from the body's left edge past the slot
    assert long.in_strip_row == short.in_strip_row


def test_a_coil_adds_its_one_contact_table_below_and_a_non_coil_adds_nothing(
    model: Model,
) -> None:
    coil = _function(model, "-K1", FunctionKind.COIL)
    keepout = _e(-56, -16, 70, 32)  # the library keep-out
    contact = _function(model, "-K1", FunctionKind.CONTACT_CO)
    assert _foot(model, contact, _COIL).standalone == keepout
    foot = _foot(model, coil, _COIL)
    rows = 2  # the two changeovers: one NO and one NC entry each
    room = table_geometry(rows, _STEP, _PAD, headed=False).height
    assert (foot.standalone.x, foot.standalone.y) == (keepout.x, keepout.y)
    assert foot.standalone.height == keepout.height + room
    assert foot.alone == keepout
    assert len(foot.no_cells) == len(foot.nc_cells) == rows
    assert foot.in_strip_row == _e(-4, -16, 18, 32)  # body and marking, no tag


def test_a_coil_with_no_contact_table_reserves_no_room(model: Model) -> None:
    """Catches a table reserved under a coil whose item owns no contacts (a relay module)."""
    coil = _function(model, "-A1", FunctionKind.COIL)
    keepout = _e(-56, -16, 70, 32)
    foot = _foot(model, coil, _COIL)
    assert foot.standalone == keepout
    assert foot.no_cells == foot.nc_cells == ()
