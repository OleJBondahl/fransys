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
from _bank_case import built_bank
from _core_solves import caught_solves
from ring_cases import bank_model, channels_model, drawn_supply_model, score_of, solved

from fransys_layout.core import pack

solve_stage = importlib.import_module("fransys_layout.core.solve")

SKID = Path(__file__).resolve().parents[3] / "examples" / "demo-skid"

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout


def lost(layout: CoreLayout) -> list[str]:
    """F (R664.G): the findings of a net drawn as a reference for want of a route; every count below is read beside it."""
    return [f.code for f in layout.findings if f.code == "WIRE_AS_REFERENCE"]


def shared_runs(layout: CoreLayout) -> list[tuple[str, str, int]]:
    """(net, net, page) of each pair whose horizontal runs lie on one y and overlap in x."""
    runs = [
        (w.net, w.page, a[1], min(a[0], b[0]), max(a[0], b[0]))
        for pr in layout.routes.pages
        for w in pr.wires
        for a, b in pairwise(w.points)
        if a[1] == b[1] and a[0] != b[0]
    ]
    return [(m[0], n[0], m[1]) for m, n in combinations(runs, 2) if m[0] != n[0] and m[1:3] == n[1:3] and m[3] < n[4] and n[3] < m[4]]


def test_trunks_of_a_flipped_fan_share_no_run_with_another_net() -> None:
    """A fan standing in flipped columns levels with the trunks on its side, not apart from them."""
    layout = solved(bank_model(8), generic=True)
    assert lost(layout) == []
    assert shared_runs(layout) == []


def test_coils_returned_to_two_channels_solve_with_no_crossing_and_no_reference() -> None:
    layout = solved(channels_model(2), generic=True)
    score = score_of(layout)
    assert lost(layout) == []
    assert (score.X, score.R, score.pages) == (0, (), 1)


def test_a_drawn_supply_closing_the_circuit_solves() -> None:
    """It solves; its one crossing is the cross-link of the net the ring through the box cut."""
    layout = solved(drawn_supply_model(), generic=True)
    assert lost(layout) == []
    assert score_of(layout).pages == 1


def _flips_and_score(model: Any) -> tuple[int, Any, list[str]]:
    """The distinct columns the solve flipped on a trial, the final score and F."""
    seen: set[str] = set()
    real = pack.flip_column

    def spy(column: Any, *, flip: bool, row: int) -> Any:
        if flip:
            seen.add(column.id)
        return real(column, flip=flip, row=row)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pack, "flip_column", spy)
        layout = solved(model, generic=True)
        return len(seen), score_of(layout), lost(layout)


@pytest.mark.parametrize(
    ("name", "model", "crossings", "pages"),
    [
        ("bank8", lambda: bank_model(8), 0, 1),
        # TAG-CORNERS: the tag of terminal 1 stands first; the wire round it has no room: one reference (looks)
        ("channels8", lambda: channels_model(8), 0, 1),
        ("bank16", lambda: bank_model(16), 24, 1),  # R745: ROW-SPREAD 21 -> 24, Covered by: RT3-FOLLOW
    ],
)
def test_a_pin_is_drawn_on_the_edge_its_column_hangs_from_so_no_column_flips(name: str, model: Any, crossings: int, pages: int) -> None:
    """BOX-SIDES A: card_edges reads each pin's own side; the sixteen-relay bank no longer cycles.

    Base 3b51cc517: bank16 flipped 12 and raised YCycleError; with every net drawn and closed
    footprint edges, bank16 crosses 21 (R549, R664).
    """
    flips, score, missing = _flips_and_score(model())
    assert len(missing) == (name == "channels8"), (
        f"{name}: only channels8 draws nets as a reference for want of a route (looks; STRIP-TAG-ONCE: 2 to 1)"
    )
    assert (flips, score.pages) == (0, pages)
    assert crossings >= score.X, f"{name}: bank16 is 21 with every net drawn (R664); its old 11 had the X1:1 feed net missing"


def test_the_demo_skid_solves_with_the_motor_bundle_pins_on_one_side() -> None:
    """BOX-SIDES B: the motor box keeps U, V and W together, so no bundle has a driver and a leg
    on one node (layout-0331) and the skid solves with no crossing.

    Two pages (was three): the skid is the unit U1 (WARN-HIDE, R881), so the relay-output
    columns re-pack. The rail terminals of -X10 and -X11 are not drawn (R315)."""
    spec = importlib.util.spec_from_file_location("demo_skid", SKID / "skid.py")
    assert spec is not None
    assert spec.loader is not None
    skid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skid)
    layout = solved(fr.build(*skid.design()).model, generic=True)
    assert lost(layout) == []
    assert (score_of(layout).X, score_of(layout).pages) == (0, 2)


@pytest.mark.rule("ROUTE-FALLBACK-REFERENCE")
def test_the_bank_of_40_draws_the_pair_k9_k25_with_no_unplaced_marker() -> None:
    """R1294, A3: the pair `-U1-K9.out` to `-U1-K25.out` that once had no path leaves no unplaced marker; a lost one would be a reference pair."""
    _, ((_, _, layout),) = caught_solves(lambda: bank_model(40))
    assert not [f for f in layout.findings if f.code == "MARKER_UNPLACED"]


def test_the_bank_of_52_plans_rows_that_hold_the_arrow_room_so_no_marker_is_unplaced() -> None:
    """R1692: the cut's row estimate adds the arrow room's dip, so the rows hold the solve's room: no MARKER_UNPLACED, no PAGE_OVERFLOW."""
    _, ((_, _, layout),) = caught_solves(lambda: bank_model(52))
    assert [f.code for f in layout.findings if f.code in ("MARKER_UNPLACED", "PAGE_OVERFLOW", "WIDER_THAN_PAGE")] == []


def test_widen_hands_no_pin_set_to_a_net_twice_on_the_bank_of_54(monkeypatch) -> None:
    """R1506: each pass of `widen` hands only links its round lost, and a handed link is never routed, so `Net.tagged` holds no pin set twice."""
    handed: list[Any] = []
    real = solve_stage.widen

    def spy(*args):
        out = real(*args)
        handed.append(out[3])
        return out

    monkeypatch.setattr(solve_stage, "widen", spy)
    caught_solves(lambda: bank_model(54))  # R1673: the banks of 40, 48, 52 and 53 lose no link now; 54 is the smallest measured that does
    tagged = [n.tagged for problem in handed for n in problem.nets if n.tagged]
    assert tagged
    assert all(len(set(t)) == len(t) for t in tagged)


def test_the_bank_of_54_draws_every_connection() -> None:
    """BANK-PIECES-JOINED (R1713): a piece of a required group a reference touches but no wire joins is joined by a loop reference, not left apart."""
    built = built_bank(54)
    assert [f for f in (*built.findings, *fr.check(built)) if f.code == "CONNECTION_NOT_DRAWN"] == []
