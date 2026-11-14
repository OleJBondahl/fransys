"""The corpus reader: 17 instances read into scenes that agree with their score files and routes."""

from itertools import pairwise

import corpus_reader
import pytest
from corpus_reader import CORPUS, corpus_names, read_instance, read_score, resided_names

NAMES = corpus_names()
READ = {n: read_instance(CORPUS / f"{n}.txt") for n in NAMES}  # one read of the corpus


def test_all_17_instances_are_read() -> None:
    assert len(NAMES) == 17


@pytest.mark.parametrize("name", NAMES)
def test_symbols_and_pages_equal_the_score_file(name: str) -> None:
    inst, want = READ[name], read_score(name)
    ids = {b.sym for b in inst.scene.boxes}
    assert len(ids) + len(inst.unplaced) == want["symbols"]
    assert len({b.page for b in inst.scene.boxes}) == want["pages"]
    assert len(inst.scene.markers) == want["references"]


def _on(pt, other) -> bool:
    return any(min(a[0], b[0]) <= pt[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= pt[1] <= max(a[1], b[1]) for a, b in pairwise(other.points))


def _anchored(w, wires, pins) -> bool:
    ends = (w.points[0], w.points[-1])
    if any((w.page, *e) in pins for e in ends):
        return True
    return any(_on(e, o) for e in ends for o in wires if o is not w and o.net == w.net and o.page == w.page)


@pytest.mark.parametrize("name", [n for n in NAMES if n not in resided_names()])
def test_every_route_runs_pin_to_pin(name: str) -> None:
    """A route has a pin at one end or meets another route of its net; a power symbol's stub (dump line `-`) is no pin of the scene."""
    scene = READ[name].scene
    pins = {(b.page, p.x, p.y) for b in scene.boxes for p in b.pins}
    for w in scene.wires:
        assert _anchored(w, scene.wires, pins)


@pytest.mark.parametrize("name", NAMES)
def test_every_marker_stands_on_its_pins_page(name: str) -> None:
    inst = READ[name]
    for m in inst.scene.markers:
        assert m.page in inst.box_pages[m.box]


def _pin_places(scene) -> set[tuple[object, ...]]:
    return {(b.page, b.sym, p.pin, p.x, p.y) for b in scene.boxes for p in b.pins}


def test_a_reader_that_ignores_orientation_moves_pins() -> None:
    """Without the R180 and MR180 turns, a turned symbol's pins read at other places."""
    saved = dict(corpus_reader.TURN)
    corpus_reader.TURN.update({"R180": (1, 1), "MR180": (1, 1)})
    try:
        scenes = [corpus_reader.read_instance(CORPUS / f"{n}.txt").scene for n in NAMES]
    finally:
        corpus_reader.TURN.update(saved)
    assert any(_pin_places(got) != _pin_places(READ[n].scene) for got, n in zip(scenes, NAMES, strict=True))


def test_a_marker_on_a_page_with_no_symbol_is_read_with_its_own_page_number(tmp_path) -> None:
    """machine_panel_large has a marker on a page the symbol lines do not name: not a KeyError."""
    text = (CORPUS / "p02_strip_to_plc.txt").read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith("marker "))
    far = line.replace("page=2 set=1", "page=9 set=9")
    assert far != line
    path = tmp_path / "far.txt"
    path.write_text(text + far + "\n", encoding="utf-8")
    pages = {m.page for m in read_instance(path).scene.markers}
    assert len(pages) > len({m.page for m in READ["p02_strip_to_plc"].scene.markers})
