"""The corpus reader: 18 instances read into scenes that agree with their score files and routes."""

import corpus_reader
import pytest
from corpus_reader import CORPUS, corpus_names, read_instance, read_score, resided_names

NAMES = corpus_names()
READ = {n: read_instance(CORPUS / f"{n}.txt") for n in NAMES}  # one read of the corpus
# Today's markers come from the built model; its routes and placements from a re-run of the
# stages. On these two builds the final layout has fewer pages than the re-run, so numbers differ.
MARKER_PAGES_DIFFER = {"w02_unit_profile", "w06_wide_controller_row"}


def test_all_18_instances_are_read() -> None:
    assert len(NAMES) == 18


@pytest.mark.parametrize("name", NAMES)
def test_symbols_and_pages_equal_the_score_file(name: str) -> None:
    inst, want = READ[name], read_score(name)
    ids = {b.sym for b in inst.scene.boxes}
    assert len(ids) + len(inst.unplaced) == want["symbols"]
    assert len({b.page for b in inst.scene.boxes}) == want["pages"]
    assert len(inst.scene.markers) == want["references"]


@pytest.mark.parametrize("name", NAMES)
def test_every_route_runs_pin_to_pin(name: str) -> None:
    if name in resided_names():
        pytest.skip("pins re-sided (BOX-SIDES Q1); the exported routes keep the old pin places")
    scene = READ[name].scene
    pins = {(b.page, p.x, p.y) for b in scene.boxes for p in b.pins}
    for w in scene.wires:
        assert (w.page, *w.points[0]) in pins
        assert (w.page, *w.points[-1]) in pins


@pytest.mark.parametrize("name", [n for n in NAMES if n not in MARKER_PAGES_DIFFER])
def test_every_marker_stands_on_its_pins_page(name: str) -> None:
    inst = READ[name]
    for m in inst.scene.markers:
        assert m.page in inst.box_pages[m.box]


@pytest.mark.parametrize("name", sorted(MARKER_PAGES_DIFFER))
def test_the_two_numberings_really_differ_where_declared(name: str) -> None:
    inst = READ[name]
    assert any(m.page not in inst.box_pages[m.box] for m in inst.scene.markers)


def test_a_reader_that_ignores_orientation_fails_the_route_check() -> None:
    """Without the R180 and MR180 turns, some routes miss their pins."""
    saved = dict(corpus_reader.TURN)
    corpus_reader.TURN.update({"R180": (1, 1), "MR180": (1, 1)})
    try:
        scenes = [corpus_reader.read_instance(CORPUS / f"{n}.txt").scene for n in NAMES]
    finally:
        corpus_reader.TURN.update(saved)
    missed = 0
    for scene in scenes:
        pins = {(b.page, p.x, p.y) for b in scene.boxes for p in b.pins}
        missed += sum((w.page, *w.points[-1]) not in pins for w in scene.wires)
    assert missed > 0


def test_a_marker_on_a_page_with_no_symbol_is_read_with_its_own_page_number(tmp_path) -> None:
    """machine_panel_large has a marker on a page the symbol lines do not name: not a KeyError."""
    text = (CORPUS / "p02_strip_to_plc.txt").read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith("marker "))
    far = line.replace("page=1 set=2", "page=9 set=9")
    assert far != line
    path = tmp_path / "far.txt"
    path.write_text(text + far + "\n", encoding="utf-8")
    pages = {m.page for m in read_instance(path).scene.markers}
    assert len(pages) > len({m.page for m in READ["p02_strip_to_plc"].scene.markers})
