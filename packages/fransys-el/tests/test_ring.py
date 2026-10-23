"""CORE-RING (layout-0327): the stage-1 y cycle on a box ring, at solve level, no facade.

Three instances raised YCycleError before. A column flipped by its box pin's edge reverses a fan
inside it (channels), a card box is one y node (drawn supply), and w08 holds both (still open).
"""

import importlib.util
from itertools import combinations, pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from ring_cases import bank_model, channels_model, drawn_supply_model, solved

from fransys_layout.core import pack

SKID = Path(__file__).resolve().parents[3] / "examples" / "demo-skid"

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout


def score_of(layout: CoreLayout) -> Any:
    """The layout's score, which `solve` always sets."""
    assert layout.score is not None
    return layout.score


def shared_runs(layout: CoreLayout) -> list[tuple[str, str, int]]:
    """(net, net, page) of each pair whose horizontal runs lie on one y and overlap in x."""
    runs = [
        (w.net, w.page, a[1], min(a[0], b[0]), max(a[0], b[0]))
        for pr in layout.routes.pages
        for w in pr.wires
        for a, b in pairwise(w.points)
        if a[1] == b[1] and a[0] != b[0]
    ]
    return [
        (m[0], n[0], m[1])
        for m, n in combinations(runs, 2)
        if m[0] != n[0] and m[1:3] == n[1:3] and m[3] < n[4] and n[3] < m[4]
    ]


def test_trunks_of_a_flipped_fan_share_no_run_with_another_net() -> None:
    """A fan standing in flipped columns levels with the trunks on its side, not apart from them."""
    assert shared_runs(solved(bank_model(8), generic=True)) == []


def test_coils_returned_to_two_channels_solve_with_no_crossing_and_no_reference() -> None:
    score = score_of(solved(channels_model(2), generic=True))
    assert (score.X, score.R, score.pages) == (0, (), 1)


def test_a_drawn_supply_closing_the_circuit_solves() -> None:
    """It solves; its one crossing is the cross-link of the net the ring through the box cut."""
    score = score_of(solved(drawn_supply_model(), generic=True))
    assert score.pages == 1


def _flips_and_score(model: Any) -> tuple[int, Any]:
    """The distinct columns the solve flipped on a trial, and the final score."""
    seen: set[str] = set()
    real = pack.flip_column

    def spy(column: Any, *, flip: bool) -> Any:
        if flip:
            seen.add(column.id)
        return real(column, flip=flip)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pack, "flip_column", spy)
        return len(seen), score_of(solved(model, generic=True))


@pytest.mark.parametrize(
    ("name", "model", "crossings", "pages"),
    [
        ("bank8", lambda: bank_model(8), 0, 1),
        ("channels8", lambda: channels_model(8), 0, 1),
        ("bank16", lambda: bank_model(16), 7, 1),
    ],
)
def test_a_pin_is_drawn_on_the_edge_its_column_hangs_from_so_no_column_flips(
    name: str, model: Any, crossings: int, pages: int
) -> None:
    """BOX-SIDES A: card_edges reads each pin's own side; the sixteen-relay bank no longer cycles.

    Measured on base 3b51cc517: bank8 flipped 4 columns (X 10), channels8 4 (X 6), bank16 flipped
    12 and raised YCycleError. With BOX-SIDES B (first half of the wired pins on N) X is 8, 0, 6
    before merging main of 2026-10-18 evening, 8, 0, 10 after (bank16 is below its base 12).
    With the lamp symbol (LAMP-SYMBOL): 0, 0, 5, bank16 on 1 page; ROUTING (R391) makes it 7:
    its ban on turning on a foreign wire, accepted as ugliness (R438).
    """
    flips, score = _flips_and_score(model())
    assert (flips, score.X, score.pages) == (0, crossings, pages), name


def test_the_demo_skid_solves_with_the_motor_bundle_pins_on_one_side() -> None:
    """BOX-SIDES B: the motor box keeps U, V and W together, so no bundle has a driver and a leg
    on one node (layout-0331) and the skid solves with no crossing.

    Three pages: the rail terminals of -X10 and -X11 are not drawn (R315), and the anchored power
    symbols' rooms set their rows' y (R408.2): Q4 and Q5 hold 40 G above page 1 row 1."""
    spec = importlib.util.spec_from_file_location("demo_skid", SKID / "skid.py")
    assert spec is not None
    assert spec.loader is not None
    skid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skid)
    score = score_of(solved(fr.build(*skid.design()).model, generic=True))
    assert (score.X, score.pages) == (0, 3)
