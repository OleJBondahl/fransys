"""R308: everything drawn at a symbol's place was placed by the core, power symbols included.

Seven cases: the demo skid and the six corpus designs. Each `DrawnSymbol` of every page Drawing is a
placed core symbol or an anchored item (same turn and origin). What is left is the unplaced stock
(table heads, junction dots, reference markers); it is a count per case that only falls, and no
power symbol is ever in it. The pump-station case joins when its example is buildable here.
"""

import importlib
import importlib.util
import sys
from collections import Counter
from pathlib import Path

import fransys as fr
import pytest
from _direct_case import built_with_unlaid, laid_again
from fransys_el import draw_write

from electrical_symbols import power_symbol_key

ROOT = Path(__file__).resolve().parent.parent
POWER_KEYS = {power_symbol_key(kind) for kind in ("supply", "ground", "pe")}

# Per case: the drawn symbols no core symbol or anchor stands behind. Only falls; the test asserts
# equality, so a fall must lower the stock and a page-blind match (R400) fails. Re-measured
# after merging frames (6f8f08ad4), whose engine draws junction dots, reference markers and
# contact heads from wires and markers; MARKER-ANCHORS and CUT-NET-ENDS turn them into anchors.
# Matched by (page, x, y, orient) since R400: a symbol on another page at the same spot no longer
# counts as placed, so the stocks rose to the page-aware counts (mcc 129, panel_di16p 251, skid 34).
# mcc rose 53 -> 127 at the merge of frames 1c46c629: its tall columns are cut (CUT-TALL), each cut
# a pair of link markers (reference-marker) that no anchor stands behind until MARKER-ANCHORS.
# skid 33 -> 34 at the merge of PIP onto frames (R395): a true junction dot (rail past K18 com,
# page 2) was counted placed because a page-1 terminal stood at the same x, y, turn.
# mcc 127 -> 128 (R408): anchor rooms recut its pages: 1 reference marker fewer, 2 dots more.
# mcc 128 -> 129 (R408.2): the rooms set the rows' y; one more reference marker (R400 figure).
# Re-measured on the merge with the text-stage tail (R448 junction dots), after the first measure on
# the text-stage tip (59f273812) with the page-aware equality test: TS's own stocks were page-blind
# and loose (`<=`); every case fell (skid 34 -> 15, mcc 129 -> 112, ...).
# RL-W2 (PORT-LINE): machine_panel 231 -> 246, panel_di16p 237 -> 244, remote_io 78 -> 82. A
# terminal on a card pin lets trunks branch there: +11, 0 and +4 junction dots, drawn from wires;
# and +4, +7 and 0 turned arrows or reference markers of the page cut. A rise: PIN-HANGINGS (R496)
# anchors them as footprint keeps.
# Covered by: PIN-HANGINGS - layout place_y/hangings; base machine_panel 22/mcc 10/remote_io 1
# (annex), 231/237/78 (unanchored): the unanchored counts are machine_panel, panel_di16p, remote_io.
# RL-W1 (R486, BUNDLE): a trunk draws one line per pole, and each pole's drop meets its own lane at
# a T that gets a dot: skid 18 -> 21, distribution_board 29 -> 44, mcc 131 -> 160 (dots only; the
# reference markers moved, none added).
# XF-UNIT-SCOPE (R514): machine_panel 246 -> 309, panel_di16p 244 -> 307, remote_io 82 -> 118, mcc
# 160 -> 170. The rise comes from UNIT-SCOPE's stub marker-arrows, a hanging kind (H1); a stub per
# line (R467). Covered by: PIN-HANGINGS - layout anchors (R496 bar, R514).
r308_unplaced_symbols = {
    "skid": 21,
    "machine_panel": 309,
    "panel_di16p": 307,
    "remote_io": 118,
    "distribution_board": 44,
    "mcc": 170,
}

# Per case: the drawn route points (every vertex of every drawn wire) that no core route point
# stands behind. Only falls. The Drawing tells a core wire from a render-made one only by point
# (no flag), so a point is core-placed if a core route, or an anchored port or lead, has it.
# Every lead and port point is one of the latter (R352 Q2), so the stock is empty; it stays a
# ceiling so a render-made wire point fails the test.
r308_unplaced_points = {
    "skid": 0,
    "machine_panel": 0,
    "panel_di16p": 0,
    "remote_io": 0,
    "distribution_board": 0,
    "mcc": 0,
}


def _skid() -> fr.BuildResult:
    spec = importlib.util.spec_from_file_location(
        "demo_skid_r308", ROOT / "examples/demo-skid/skid.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return fr.build(*module.design())


def _corpus(name: str):
    def build() -> fr.BuildResult:
        sys.path.insert(0, str(ROOT / "internal"))
        module = importlib.import_module(f"placement_corpus.standard.{name}")
        return fr.build(*module.design())

    return build


BUILDS = {"skid": _skid, **{n: _corpus(n) for n in list(r308_unplaced_symbols)[1:]}}
# The corpus cases read internal/, so the export skips them (R462); the skid case runs there.
CASE_PARAMS = [
    n if n == "skid" else pytest.param(n, marks=pytest.mark.private_input) for n in BUILDS
]


def _drawn_and_layouts(name: str):
    """(all page Drawings, each drawing set's core layout, each set's layout with its pages)."""
    _, unlaid = built_with_unlaid(BUILDS[name])
    sets = []
    real = draw_write.draw_set

    def spy(model, layout, problem, kit, pages, **kwargs):
        sets.append((layout, pages))
        return real(model, layout, problem, kit, pages, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(draw_write, "draw_set", spy)
        _, drawn, _ = laid_again(unlaid)
    return drawn, [lo for lo, _ in sets], sets


@pytest.fixture(scope="module", params=CASE_PARAMS)
def case(request: pytest.FixtureRequest):
    drawn, layouts, sets = _drawn_and_layouts(request.param)
    placed = Counter()
    anchored = Counter()
    for layout, pages in sets:
        for page in layout.placement.pages:
            placed.update((pages[page.page].id, p.x, p.y, p.orient) for p in page.placed)
        for a in layout.annotations.anchored:
            placed[(pages[a.page].id, a.x, a.y, a.orient)] += 1
            anchored[(a.x, a.y, a.orient)] += 1
    symbols = [(page, s) for page, d in drawn.items() for s in d.symbols]
    stood = {pt for lo in layouts for pg in lo.routes.pages for w in pg.wires for pt in w.points}
    for lo in layouts:
        for a in lo.annotations.anchored:
            stood.update((a.port, *a.lead))
    points = [pt for d in drawn.values() for w in d.wires for pt in w.points]
    return request.param, symbols, placed, anchored, [pt for pt in points if pt not in stood]


@pytest.mark.rule("PLACEMENT")
def test_every_drawn_symbol_is_a_placed_symbol_or_an_anchor_but_a_falling_stock(case):
    name, symbols, placed, _, _ = case
    unplaced = [s for page, s in symbols if (page, s.x, s.y, s.orient) not in placed]
    assert len(unplaced) == r308_unplaced_symbols[name], (  # equal: a lower count lowers the stock
        len(unplaced),
        sorted({s.key for s in unplaced}),
    )
    assert not [s for s in unplaced if s.key in POWER_KEYS]


def test_each_power_symbol_is_an_anchor_the_core_placed(case):
    name, symbols, _, anchored, _ = case
    power = Counter((s.x, s.y, s.orient) for _, s in symbols if s.key in POWER_KEYS)
    assert power == anchored, name


@pytest.mark.rule("PLACEMENT")
def test_every_drawn_route_point_is_a_core_route_point_but_a_falling_stock(case):
    name, _, _, _, unstood = case
    assert len(unstood) <= r308_unplaced_points[name], (len(unstood), unstood[:6])
