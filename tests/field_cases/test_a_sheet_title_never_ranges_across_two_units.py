"""Field case: a sheet title never reads "A to B" across two units.

The engineering shape: a cabinet's own blocks "Feed 1" and "Feed 2" share a sheet with a nested
relay board's block; the board is a unit of its own.

The bug: the title offered the range "Relay board to Feed 2", which names a span from the
board's unit into the cabinet's.

The rule (decision layout-0268, PAGE-TITLE-FIT T2): a range never spans two units. A sheet that
holds groups of two units composes by T1: the joined texts, then the lead and "n more".
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
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
    u.detail.wire(x[1], lamp["1"], wire=(BK, 0.5))
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
    u.detail.wire(h1["1"], h2["2"], wire=(BK, 0.5))
    return _Open()


@pytest.fixture(scope="module")
def forms(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, ...]:
    d = fr.design("demo_parts")
    d.add(_cabinet, "C1", place=None)
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
    ).model
    sets = layout_of(model, DrawingSet)
    (found,) = (
        page_title_forms(model, page)
        for page in layout_of(model, Page).values()
        if (owner := sets[page.drawing_set].unit) is not None
        and unit_release(model, owner).name == "demo-cab"
    )
    return found


def test_no_form_is_a_range_across_the_two_units(forms: tuple[str, ...]) -> None:
    assert not any(" to " in form for form in forms)


def test_the_forms_are_the_joined_texts_then_the_lead_and_n_more(forms: tuple[str, ...]) -> None:
    assert forms == ("Relay board, Feed 1, Feed 2", "Relay board and 2 more")
