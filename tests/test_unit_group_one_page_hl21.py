"""Acceptance 16 (HL21): the study board's unit group stays on one page and moves whole.

The group is the outline, its interfaces, the plug boxes on them and the columns its lines
reach. Before layout-0153 P2c its last lower-band column spilled onto a second page, which drew
a second outline with the same boxes. Built through `fr` from `demo_parts`, with and without
the side hint (one module fixture per build).
"""

import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from fransys_model import derive
from fransys_model.layout import ConnectorBox, Outline, SymbolPlacement, layout_of

if TYPE_CHECKING:
    import fransys as fr

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ha_study_board import build  # noqa: E402 -- needs the tests folder on sys.path first

BOXES = {"-U1-J1", "-U1-J2", "-U1-J3", "-U1-J5", "-U1-J7"}
BOXES |= {"-W11-P11", "-W12-P12", "-W13-P13", "-W15-P15", "-W17-P17"}
# items in the columns the group's lines reach (its bands): K1 and J10 below, A1, P18
BAND_ITEMS = ("A1:", "K1:", "W17-P18:")


@pytest.fixture(scope="module", params=[False, True], ids=["no-hint", "hint"])
def board(request: pytest.FixtureRequest) -> fr.BuildResult:
    return build(hint=request.param)


def _box_pages(result: fr.BuildResult) -> dict[str, list[Any]]:
    """Each box's pages among those with an outline (the unit's own pages draw its boxes too)."""
    framed = {o.page for o in layout_of(result.model, Outline).values()}
    found: dict[str, list[Any]] = {}
    for box in layout_of(result.model, ConnectorBox).values():
        if box.page not in framed:
            continue
        name = derive.connector_box_lines(result.model, box.function)[0]
        found.setdefault(name, []).append(box.page)
    return found


def _outline_page(result: fr.BuildResult) -> Any:
    """The one page holding a middle outline: the page every one of the group's boxes is on."""
    pages = _box_pages(result)
    outlines = [o.page for o in layout_of(result.model, Outline).values()]
    held = [page for page in outlines if all(page in pages[name] for name in BOXES)]
    assert len(held) == 1, held
    return held[0]


def test_every_box_of_the_group_stands_once_on_the_outlines_page(board: fr.BuildResult) -> None:
    page = _outline_page(board)
    pages = _box_pages(board)
    assert {name: pages[name] for name in BOXES} == {name: [page] for name in BOXES}


def test_the_unit_has_one_outline_and_no_second_copy_on_another_page(
    board: fr.BuildResult,
) -> None:
    page = _outline_page(board)
    counted = Counter(o.page for o in layout_of(board.model, Outline).values())
    assert counted[page] == 1
    pages = _box_pages(board)
    assert not [name for name in BOXES if len(pages[name]) != 1]


def test_the_band_columns_stand_on_the_outlines_page(board: fr.BuildResult) -> None:
    page = _outline_page(board)
    placed: dict[str, set[Any]] = {}
    for one in layout_of(board.model, SymbolPlacement).values():
        name = derive.function_designation(board.model, one.function)
        placed.setdefault(name.split(":")[0] + ":", set()).add(one.page)
    assert {item: placed[item] for item in BAND_ITEMS} == {item: {page} for item in BAND_ITEMS}
