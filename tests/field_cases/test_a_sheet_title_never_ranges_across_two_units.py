"""Field case: a cabinet's own blocks Feed 1 and Feed 2 share a sheet with a nested relay board's block, which is a unit of its own.
The bug: the title offered the range "Relay board to Feed 2", a span from the board's unit into the cabinet's.
Fixed by layout-0268 (PAGE-TITLE-FIT T2), a range never spans two units; a sheet holding groups of two units composes by T1."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BK

from fransys_model.derive import page_title_forms, unit_release
from fransys_model.layout import DrawingSet, Page, layout_of


class _Open(NamedTuple):
    pass


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit(
    "demo-board",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Relay board",
)
def _board(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    with u.function("F1", "Board circuit"):
        x = u.device("X1", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
        lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.series(x[1], lamp["1"], wire=(BK, 0.5))
    u.series(x[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x)


@fr.unit(
    "demo-cab",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Cabinet",
)
def _cabinet(u: Any) -> _Open:
    with u.function("P1", "Feed 1"):
        h1 = u.device("H1", "DEMO-LAMP-24")
    board = u.add(_board, "U1")
    with u.function("P2", "Feed 2"):
        h2 = u.device("H2", "DEMO-LAMP-24")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X1[1], h2["1"])
    cable.core(2, board.X1[2], h1["2"])
    u.series(h1["1"], h2["2"], wire=(BK, 0.5))
    return _Open()


@pytest.fixture(scope="module")
def forms() -> tuple[str, ...]:
    d = fr.design("demo_parts")
    d.add(_cabinet, "C1", place=None)
    model = fr.build(d, unit_document("demo-cab")).model
    sets = layout_of(model, DrawingSet)
    (found,) = (
        page_title_forms(model, page)
        for page in layout_of(model, Page).values()
        if (owner := sets[page.drawing_set].unit) is not None and unit_release(model, owner).name == "demo-cab"
    )
    return found


def test_no_form_names_the_board_the_page_does_not_draw(forms: tuple[str, ...]) -> None:
    """The board's groups stand on its own sheets (model-0405), so no form ranges from the board into the cabinet."""
    assert not any("Relay board" in form for form in forms)


def test_the_forms_are_the_joined_texts_then_the_lead_and_n_more(forms: tuple[str, ...]) -> None:
    assert forms == ("Feed 1, Feed 2", "Feed 1 to 2")
