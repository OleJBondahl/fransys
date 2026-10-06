"""List headings of a unit's own document (pdf-0012): unit-relative, and the terminal sides.

4a (R2/D12). A unit's own document heads each strip's table with the strip's designation read
unit-relative (`-X2`), as the rows below it already are; a location document keeps the full
text (`-JB1-X2`, a strip inside a board). 4b (model-0054 section 3). The two ends columns of a
strip's terminal list are headed by the terminal part's port markings when the part names both
its internal and its external port, else "Side A" / "Side B". No demo part carries a marking,
so 4b builds a throwaway part library in `tmp_path` (never `examples/demo-parts`).
"""

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from fransys_pdf import _lists

from fransys_model.vocab import DocumentPreset
from fransys_model.vocab.tables import aspect_nodes, documents

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`;
# `fransys_pdf`'s own hand-built model helpers are loaded from their file by path, as
# `test_csv_agrees_with_pdf_lists.py` does (the same module object, one registered name).
_BUILD_PATH = (
    Path(__file__).resolve().parent.parent / "packages" / "fransys-pdf" / "tests" / "_build.py"
)
if "_pdf_tests_build" in sys.modules:
    _build = sys.modules["_pdf_tests_build"]
else:
    _build_spec = importlib.util.spec_from_file_location("_pdf_tests_build", _BUILD_PATH)
    assert _build_spec is not None
    assert _build_spec.loader is not None
    _build = importlib.util.module_from_spec(_build_spec)
    sys.modules["_pdf_tests_build"] = _build
    _build_spec.loader.exec_module(_build)

# -- 4a: unit-relative headings ----------------------------------------------------------------


@pytest.fixture(scope="module")
def board_strip():
    """(model, the unit's document, the location's document): strip `X2` under board `JB1`.

    Unit `u1` has the board as its sole root; the strip is the board's child and `T:1` is wired
    to a device `B12`, so the strip's table has a row. Both are placed at `C1`.
    """
    c1 = _build.location("C1", "Demo cabinet")
    u = _build.unit("u1", name="io-board")
    unit_doc = _build.document(
        "d-unit", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# Cover"
    )
    location_doc = _build.document(
        "d-loc", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover"
    )
    board_part = _build.part("board1", description="Invented board")
    board = _build.item("jb1", description="Board one", part=board_part.id, unit=u.id)
    strip = _build.item("x2", description="Strip two", parent=board.id, unit=u.id)
    child, facet, fn, internal = _build.bridged_terminal("t1", strip=strip.id, group="T", index=1)
    child = replace(child, unit=u.id)
    b12, b12_fn, b12_port = _build.pin("b12", "B12", unit=u.id)
    b12 = replace(b12, parent=board.id)  # inside the board: the board stays the unit's sole root
    wire = _build.conductor("w1", a=internal.id, b=b12_port.id)
    records = (c1, u, unit_doc, location_doc, board_part, board, strip, child, facet, fn, internal)
    records += (b12, b12_fn, b12_port, wire)
    records += (_build.pcb_facet("board1", subject=board_part.id),)
    records += tuple(
        _build.place(key, item=item.id, node=c1.id)
        for key, item in (("p-strip", strip), ("p-b12", b12), ("p-jb1", board))
    )
    model = _build.model(*records)
    return model, documents(model)[unit_doc.id], documents(model)[location_doc.id]


def test_a_units_own_terminal_list_heads_its_strip_unit_relative(board_strip):
    model, unit_doc, _location_doc = board_strip
    page = _lists.terminal_list_page(model, unit_doc)
    assert '#heading(level: 2, text("-X2"))' in page
    assert "-JB1-X2" not in page.split("#table")[0]  # not in the heading
    assert 'text("-X2:T:1")' in page  # the table's row is there, unit-relative too


def test_a_location_documents_terminal_list_keeps_the_strips_full_heading(board_strip):
    model, _unit_doc, location_doc = board_strip
    page = _lists.terminal_list_page(model, location_doc)
    assert '#heading(level: 2, text("-JB1-X2"))' in page
    assert 'text("-JB1-X2:T:1")' in page


# -- 4b: the terminal list's Side A / Side B headings from the part's port markings ------------

_INTERNAL = '{ name = "internal", role = "internal", symbol_port = "n"'
_EXTERNAL = '{ name = "external", role = "external", symbol_port = "s"'


def _port(base: str, marking: str | None) -> str:
    return base + ("" if marking is None else f', marking = "{marking}"') + " }"


def _library(root: Path, parts: dict[str, tuple[str | None, str | None]]) -> Path:
    """`demo_parts` copied to `root`, plus one terminal part per `parts` entry (mpn -> markings).

    Each new part is `terminal-feedthrough-2_5.toml` with its `mpn` and its two ports' `marking`
    replaced: `None` writes no `marking` (the port prints its name), `""` writes the empty one.
    """
    import shutil

    import demo_parts

    library = root / "demo_parts"
    shutil.copytree(Path(demo_parts.__file__).parent, library, ignore=shutil.ignore_patterns("__*"))
    base = (library / "parts" / "terminal-feedthrough-2_5.toml").read_text(encoding="utf-8")
    assert _port(_INTERNAL, None) in base
    assert _port(_EXTERNAL, None) in base
    for index, (mpn, (internal, external)) in enumerate(parts.items()):
        if mpn == "DEMO-TB-2.5":  # the shipped part, already in the library
            continue
        text = base.replace('mpn = "DEMO-TB-2.5"', f'mpn = "{mpn}"')
        text = text.replace(_port(_INTERNAL, None), _port(_INTERNAL, internal))
        text = text.replace(_port(_EXTERNAL, None), _port(_EXTERNAL, external))
        (library / "parts" / f"terminal-test-{index}.toml").write_text(text, encoding="utf-8")
    return library


def _terminal_page(tmp_path: Path, markings: dict[str, tuple[str | None, str | None]]) -> str:
    """The terminal list page of one strip `X1` with a terminal of each `markings` part.

    Every terminal is wired on both sides (to relay `K1`), so neither ends column is dropped
    (pdf-0011): a missing heading is then never an empty-column effect.
    """
    parts = fransys_parts.load_path(_library(tmp_path, markings))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d = fransys_author.Design(parts)
    d.project(title="T", number="1", customer="C", revision=1, author="A")
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    grp = d.group("G", "Group")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=grp)
    strip = d.strip("X1", at=c1)
    wire = d.wiring(colour="BU", gauge="0.5")
    coil, co1 = k1.fn("coil"), k1.fn("co_1")
    for number, mpn in enumerate(markings, start=1):
        terminal = strip.terminal(mpn, "T", index=number, group=grp)
        wire(terminal.inner, coil["A1"] if number == 1 else co1["11"], n=number)
        wire(terminal.outer, coil["A2"] if number == 1 else co1["12"], n=number)
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    model = fr.build(parts, d.draft(), document).model
    location = next(node.id for node in aspect_nodes(model).values() if node.label == "C1")
    (record,) = (r for r in documents(model).values() if r.location == location)
    return _lists.terminal_list_page(model, record)


def _headers(page: str) -> list[str]:
    import re

    return re.findall(r'strong\(text\("([^"]*)"\)\)', page)


def test_a_part_naming_both_ports_heads_the_sides_by_its_markings(tmp_path):
    page = _terminal_page(tmp_path, {"DEMO-TB-MARKED": ("Cabinet", "Field")})
    headers = _headers(page)
    assert "Cabinet" in headers
    assert "Field" in headers
    assert headers.index("Cabinet") < headers.index("Field")  # internal first
    assert "Side A" not in headers
    assert "Side B" not in headers
    assert 'text("-X1:T:1")' in page  # the rows are there


def test_an_unmarked_part_keeps_side_a_and_side_b(tmp_path):
    page = _terminal_page(tmp_path, {"DEMO-TB-2.5": (None, None)})
    assert {"Side A", "Side B"} <= set(_headers(page))


def test_a_part_naming_only_one_port_keeps_side_a_and_side_b(tmp_path):
    page = _terminal_page(tmp_path, {"DEMO-TB-INT": ("Cabinet", None)})
    headers = _headers(page)
    assert {"Side A", "Side B"} <= set(headers)
    assert "Cabinet" not in headers


def test_an_empty_marking_is_not_a_name(tmp_path):
    page = _terminal_page(tmp_path, {"DEMO-TB-EMPTY": ("Cabinet", "")})
    headers = _headers(page)
    assert {"Side A", "Side B"} <= set(headers)
    assert "Cabinet" not in headers


def test_two_marking_pairs_on_one_strip_keep_side_a_and_side_b(tmp_path):
    page = _terminal_page(
        tmp_path,
        {"DEMO-TB-M1": ("Cabinet", "Field"), "DEMO-TB-M2": ("Panel", "Yard")},
    )
    headers = _headers(page)
    assert {"Side A", "Side B"} <= set(headers)
    assert not {"Cabinet", "Field", "Panel", "Yard"} & set(headers)


def test_terminals_of_one_pair_from_two_parts_still_take_the_markings(tmp_path):
    """One distinct pair, not one part: two parts naming the same pair head the sides by it."""
    page = _terminal_page(
        tmp_path,
        {"DEMO-TB-M1": ("Cabinet", "Field"), "DEMO-TB-M2": ("Cabinet", "Field")},
    )
    headers = _headers(page)
    assert {"Cabinet", "Field"} <= set(headers)
    assert "Side A" not in headers


@pytest.fixture(scope="module")
def board_in_board():
    """(model, the unit's document, the location's document): board `JB2` inside board `JB1`.

    Both are `pcb` boards of unit `u1`; `JB1` is the unit's sole root, `JB2` is its child with
    connector `J1`. Both are placed at `C1`.
    """
    c1 = _build.location("C1", "Demo cabinet")
    u = _build.unit("u1", name="io-board")
    unit_doc = _build.document(
        "d-unit", preset=DocumentPreset.PCB_SCHEMATIC, subject=u, cover="# Cover"
    )
    location_doc = _build.document(
        "d-loc", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover"
    )
    outer_part = _build.part("outer", description="Outer board")
    inner_part = _build.part("inner", description="Inner board")
    outer = _build.item("jb1", description="Board one", part=outer_part.id, unit=u.id)
    inner = _build.item(
        "jb2", description="Board two", part=inner_part.id, parent=outer.id, unit=u.id
    )
    conn = _build.connector("j1", item=inner.id, name="J1", markings=("1",))
    records = (c1, u, unit_doc, location_doc, outer_part, inner_part, outer, inner)
    records += (
        _build.pcb_facet("outer", subject=outer_part.id),
        _build.pcb_facet("inner", subject=inner_part.id),
        *conn[:4],
        *conn[4],
    )
    records += tuple(
        _build.place(key, item=item.id, node=c1.id)
        for key, item in (("p-jb1", outer), ("p-jb2", inner))
    )
    model = _build.model(*records)
    return model, documents(model)[unit_doc.id], documents(model)[location_doc.id]


def test_a_units_own_connector_list_heads_an_inner_board_unit_relative(board_in_board):
    model, unit_doc, _location_doc = board_in_board
    page = _lists.connector_list_page(model, unit_doc)
    assert '#heading(level: 2, text("-JB2"))' in page
    assert "-JB1-JB2" not in page
    assert 'text("-JB2"), text("header")' in page  # the connector row is there


def test_a_location_documents_connector_list_keeps_the_inner_boards_full_heading(board_in_board):
    model, _unit_doc, location_doc = board_in_board
    page = _lists.connector_list_page(model, location_doc)
    assert '#heading(level: 2, text("-JB1-JB2"))' in page
