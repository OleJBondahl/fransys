"""The canary and the rename test: every list an engineer reads prints in natural order.

Engineering shape: one invented design whose every tag family holds the members 1, 2, 10 and 11,
declared out of order: relays, contactors, lamps, terminal strips, harnesses and their cables,
units, locations, a part-less generic box with ports 1, 2, 10 and 11, a contactor's contact
functions, and a board net with the pins 2 and 10. The design is built and written once under a
first set of `name=` keys and once under a second set, so every Id changes and no printed text may.

Canary: each CSV list, each PDF list, the loom page order, the overview's items, the generic
box ports, the KiCad net name and the findings print `-X2` before `-X10`.
Rename: a change of the keys changes no CSV byte, no overview page byte (the page holds no Id, A10),
no PDF text run on any page and no netlist byte. SVG draw order is not compared: it changes
bytes, not the picture. Every `fr.check` finding message also reads the same, in finding order
(FT3, overview-0003): a variant design raises the codes that used to print keys.

Each site that fails today is its own strict xfail, so its test flips when its fix lands.
The sites not reached: the wago XML (no PLC channel in the design), the unit block-diagram sheets
and the drawing-set order of units and locations (a document prints one drawing set, and a block
diagram needs a top-level cable between units).
Fixing decision: test-0136 (the canary and the rename test join the gate).
"""

import csv
import io
import json
import re
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pypdfium2
import pytest
from fransys.colours import BK, GNYE, RD

from fransys_layout import lay_out_overview
from fransys_model.layout import OverviewBox, OverviewLine, layout_of

if TYPE_CHECKING:
    from pathlib import Path

_NS = (10, 1, 11, 2)
_NATURAL = ["1", "2", "10", "11"]
_TAG = re.compile(r"[-+=]([A-Z]+)(\d+)(?![0-9])")
_PAGE_TITLE = re.compile(r"Page title\r?\n(?!Scope)([^\r\n]+)")
_ITEM_ID = re.compile(r"item:[0-9a-f]{32}")
_CSVS = (
    "bom",
    "cables",
    "designations",
    "plc",
    "wires",
    *(f"connectors-U{n}" for n in _NS),
    *(f"terminals-C1-X{n}" for n in _NS),
)
_SHARED = ("Designation list", "Cable list", "BOM")
_NOT_LISTS = ("Cover", "Contents", "schematic")
_PAGES = {
    "C1.pdf": ("Cover", "schematic", "Terminal list", "Wire label list", *_SHARED),
    "v1.1.pdf": ("Cover", "Contents", "Wire label list", *_SHARED),
}


class _Io(NamedTuple):
    J1: fr.Fn


class _Page(NamedTuple):
    """One PDF page: its text in stream order, and its glyphs sorted by position."""

    text: str
    runs: tuple[tuple[float, float, str], ...]


class _Run(NamedTuple):
    """One build of the canary and everything it wrote, read back as text and bytes."""

    result: fr.BuildResult
    files: dict[str, bytes]
    pdfs: dict[str, tuple[_Page, ...]]
    netlists: dict[str, str]
    svgs: dict[str, str]


def _board(salt: str):
    @fr.unit(
        "demo-canary-board",
        revision=1,
        interface_version=1,
        date="2026-10-08",
        text="First",
        by="AB",
        title="Board",
        number="B-1",
    )
    def board(u: fr.Design) -> _Io:
        pcb = u.device("A1", "DEMO-PCB-IO", name=f"{salt}pcb")
        j1 = u.device("J1", "DEMO-CONN-4P-MIXED", parent=pcb, unused=True, name=f"{salt}j1")
        u.wire(j1["2"], j1["10"], wire=(BK, 0.5))
        return _Io(j1.x1)

    return board


def _loom(d: fr.Design, n: int, salt: str) -> None:
    harness = d.harness(f"WH{n}", place="C1", name=f"{salt}wh{n}")
    j1 = d.device("J1", "DEMO-CONN-2P", parent=harness, place="C1", name=f"{salt}wj1-{n}")
    j2 = d.device("J2", "DEMO-CONN-2P", parent=harness, place="C1", name=f"{salt}wj2-{n}")
    cable = d.cable(f"W{n}", "DEMO-CBL-4G1.5", parent=harness, place="C1", name=f"{salt}w{n}")
    cable.core(1, j1[1], j2[1])


def _circuit(d: fr.Design, strips: dict[int, fr.TerminalStrip], n: int, salt: str) -> None:
    k = d.device(f"K{n}", "DEMO-RLY-2CO-24", place="C1", name=f"{salt}k{n}")
    q = d.device(f"Q{n}", "DEMO-CTR-3P-NC", place="C1", name=f"{salt}q{n}")
    h = d.device(f"H{n}", "DEMO-LAMP-24", place=f"L{n}", name=f"{salt}h{n}")
    d.wire(strips[1][1].inner, q.coil["A1"], wire=(RD, 0.75))
    d.wire(q.coil["A2"], k.coil["A1"], wire=(RD, 0.75))
    d.wire(k.coil["A2"], strips[2][n].inner, wire=(BK, 0.75))
    d.wire(q.aux_nc["21"], k.co_2["21"], wire=(RD, 0.75))
    d.wire(q.aux["13"], k.co_1["11"], wire=(RD, 0.75))
    d.wire(q.main["1"], strips[10][n].inner, wire=(RD, 0.75))
    d.wire(k.co_1["14"], h[1], wire=(RD, 0.75))
    with d.function(f"F{n}", f"Loom {n}"):
        _loom(d, n, salt)


def _design(salt: str) -> tuple[fr.Design, Any]:  # the location handle is not a public name
    d = fr.design("demo_parts")
    d.project(title="Canary", number="CAN-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-08", text="First", created="XX")
    for n in _NS:
        d.location(f"L{n}", f"Place {n}")
    cabinet = d.location("C1", "Cabinet")
    strips = {
        n: d.terminal_strip(f"X{n}", "DEMO-TB-2.5", 12, place="C1", name=f"{salt}x{n}") for n in _NS
    }
    board = _board(salt)
    boards = {n: d.add(board, f"U{n}", name=f"{salt}u{n}") for n in _NS}
    link = d.cable("W9", "DEMO-CBL-4G1.5", place="C1", name=f"{salt}w9")
    link.core(1, boards[_NS[0]].J1["1"], boards[_NS[1]].J1["1"])  # the system level holds a line
    d.device("B1", None, external=True, pins=("10", "1", "11", "2"), place="C1", name=f"{salt}box")
    for n in _NS:
        _circuit(d, strips, n, salt)
    return d, cabinet


def _page(page: pypdfium2.PdfPage) -> _Page:
    """A page's text in stream order, and its glyphs sorted by position (the picture).

    Glyphs, not pdfium's text runs: two overlapping blocks drawn in another order chunk into other
    runs, while every glyph stays where it is.
    """
    text = page.get_textpage()
    glyphs = (
        (round(left), round(bottom), text.get_text_range(i, 1))
        for i in range(text.count_chars())
        for left, bottom, _, _ in [text.get_charbox(i)]
        if text.get_text_range(i, 1).strip()  # pdfium's spaces and line ends are its own
    )
    return _Page(text.get_text_range(), tuple(sorted(glyphs)))


def _pdf_pages(path: Path) -> tuple[_Page, ...]:
    document = pypdfium2.PdfDocument(path)
    try:
        return tuple(_page(page) for page in document)
    finally:
        document.close()


def _run(salt: str, root: Path) -> _Run:
    d, cabinet = _design(salt)
    covers = {stem: root / f"{stem}.md" for stem in ("cabinet", "system")}
    for stem, cover in covers.items():
        cover.write_text(f"# {stem}\n", encoding="utf-8")
    pages = tuple(kind for kind in fr.PageKind if kind is not fr.PageKind.HARNESS_DRAWING)
    cabinet_doc = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=covers["cabinet"], add=pages
    )
    system_doc = fr.document(
        fr.DocumentPreset.SYSTEM,
        None,
        cover=covers["system"],
        add=tuple(kind for kind in pages if kind is not fr.PageKind.SCHEMATIC),
    )
    result = fr.build(d, cabinet_doc, system_doc)
    out, inter = root / "out", root / "inter"
    fr.write(result, out_dir=out, intermediates=inter)
    exports = sorted(path for path in out.iterdir())
    return _Run(
        result=result,
        files={p.name: p.read_bytes() for p in exports if p.suffix != ".pdf"},
        pdfs={p.name: _pdf_pages(p) for p in exports if p.suffix == ".pdf"},
        netlists={p.name: p.read_text() for p in sorted(inter.glob("netlist-*.net"))},
        svgs={p.name: p.read_text() for p in sorted(inter.glob("*.svg"))},
    )


@pytest.fixture(scope="module")
def first(tmp_path_factory: pytest.TempPathFactory) -> _Run:
    """The canary under its first keys."""
    return _run("a-", tmp_path_factory.mktemp("first"))


@pytest.fixture(scope="module")
def second(tmp_path_factory: pytest.TempPathFactory) -> _Run:
    """The canary under a second salt of every `name=` key, so every Id changes."""
    return _run("b-", tmp_path_factory.mktemp("second"))


def _file(run: _Run, suffix: str) -> bytes:
    (name,) = (n for n in run.files if n.endswith((f"-{suffix}", f"-{suffix}.csv")))
    return run.files[name]


def _pdf(run: _Run, name: str) -> tuple[_Page, ...]:
    (found,) = (n for n in run.pdfs if n.endswith(name))
    return run.pdfs[found]


def _out_of_order(text: str) -> dict[str, list[int]]:
    """Each tag family whose members first appear in `text` in another order than ascending."""
    seen: dict[str, list[int]] = {}
    for family, number in _TAG.findall(text):
        run = seen.setdefault(family, [])
        if int(number) not in run:
            run.append(int(number))
    return {family: run for family, run in seen.items() if run != sorted(run)}


def _natural(items: list[str]) -> bool:
    return items == sorted(items, key=fr.derive.natural_key)


_LIST_TITLES = {t for titles in _PAGES.values() for t in titles} - {"schematic"}


def _title(page: str) -> str:
    """The page's list title; any other title (a schematic page's own) groups as "schematic"."""
    found = _PAGE_TITLE.search(page)
    title = found.group(1).strip() if found else ""
    return title if title in _LIST_TITLES else "schematic"


def _by_title(pages: tuple[_Page, ...]) -> dict[str, list[_Page]]:
    """A PDF's pages grouped by page title, pages in order."""
    titled: dict[str, list[_Page]] = {}
    for page in pages:
        titled.setdefault(_title(page.text), []).append(page)
    return titled


def _text(pages: list[_Page]) -> str:
    return "\n".join(page.text for page in pages)


def _rows(run: _Run, suffix: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_file(run, suffix).decode())))


# ---- O1: the canary -------------------------------------------------------------------------


def _open(reason: str) -> pytest.MarkDecorator:
    """A site whose fix has not landed: strict, so its test flips when the fix does."""
    return pytest.mark.xfail(strict=True, reason=reason)


def _params(cases: list[tuple], open_sites: dict[tuple, str]) -> list:
    """Each case as a param; a case in `open_sites` carries that site's strict xfail."""
    return [
        pytest.param(
            *case,
            marks=_open(open_sites[case]) if case in open_sites else (),
            id="-".join(map(str, case)),
        )
        for case in cases
    ]


@pytest.mark.parametrize(
    "name",
    _params(
        [(name,) for name in _CSVS],
        {},
    ),
)
def test_each_csv_prints_its_tags_in_natural_order(first: _Run, name: str) -> None:
    text = _file(first, name).decode()
    if name.startswith("connectors"):  # the Ends column names wherever a wire goes (L18)
        text = "\n".join(line.rsplit(",", 1)[0] for line in text.splitlines())
    assert _out_of_order(text) == {}


@pytest.mark.parametrize("n", _NS)
def test_a_connector_csv_lists_its_pins_in_natural_order(first: _Run, n: int) -> None:
    markings = [row["marking"] for row in _rows(first, f"connectors-U{n}")]
    assert markings == ["1", "2", "10", "A1"]


def test_a_terminals_far_ends_print_in_natural_order(first: _Run) -> None:
    (hub,) = (row for row in _rows(first, "terminals-C1-X1") if row["index"] == "1")
    ends = hub["side_a"].split("; ")
    assert ends == [f"+C1-Q{n}:A1" for n in (1, 2, 10, 11)]


@pytest.mark.parametrize(
    ("pdf", "title"),
    _params(
        [
            (pdf, title)
            for pdf, titles in _PAGES.items()
            for title in titles
            if title not in _NOT_LISTS
        ],
        {},
    ),
)
def test_each_pdf_list_prints_its_tags_in_natural_order(first: _Run, pdf: str, title: str) -> None:
    assert _out_of_order(_text(_by_title(_pdf(first, pdf))[title])) == {}


def test_the_loom_groups_run_in_natural_order_on_their_page(first: _Run) -> None:
    pages = _pdf(first, "C1.pdf")
    (title,) = {
        m.group(0) for page in pages if (m := re.search(r"Loom \d+(?:, Loom \d+)+", page.text))
    }
    assert title.split(", ") == [f"Loom {n}" for n in (1, 2, 10, 11)]


def test_the_kicad_net_is_named_by_its_lowest_pin(first: _Run) -> None:
    assert '(name "Net-(J1-2)")' in first.netlists["netlist-U1.net"]


def test_the_generic_box_draws_its_ports_left_to_right_in_natural_order(first: _Run) -> None:
    (svg,) = (s for s in first.svgs.values() if ">-B1<" in s)
    texts = re.findall(r'<text[^>]* x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>', svg)
    label_y = next(float(y) for _, y, text in texts if text == "-B1")
    near = sorted(
        (float(x), float(y), text)
        for x, y, text in texts
        if text in _NATURAL and abs(float(y) - label_y) < 5
    )
    assert [text for _, _, text in near] == _NATURAL


def _overview(run: _Run) -> dict:
    html = _file(run, "overview.html").decode()
    found = re.search(r'id="overview-data">(.*?)</script>', html, re.DOTALL)
    assert found is not None
    return json.loads(found.group(1))


def test_the_overview_lists_its_items_by_natural_designation(first: _Run) -> None:
    labels = [item["label"] for item in _overview(first)["items"]]
    keys = [fr.derive.natural_key(label) for label in labels]
    assert len(labels) > len(_NS)
    assert keys == sorted(keys)


def _designation(model: fr.Model, subject) -> str:
    if subject.kind == "port":
        return fr.derive.port_designation(model, subject)
    return fr.derive.item_designation(model, subject)


@pytest.mark.parametrize("code", ["FUNCTION_HALF_CONNECTED", "ITEM_WITHOUT_PART"])
def test_findings_of_one_code_list_by_natural_designation(first: _Run, code: str) -> None:
    found = [f for f in first.result.findings if f.code == code]
    printed = [_designation(first.result.model, f.subjects[0]) for f in found]
    assert len(printed) > len(_NS)
    assert _natural(printed)


# ---- O2: the rename test --------------------------------------------------------------------


def test_the_rename_changes_the_id_of_every_keyed_item(first: _Run, second: _Run) -> None:
    def keyed(run: _Run) -> set:
        return {f.subjects[0] for f in run.result.findings if f.code == "ITEM_WITHOUT_PART"}

    assert len(keyed(first)) == len(_NS) * 2
    assert keyed(first).isdisjoint(keyed(second))


def test_the_rename_changes_no_file_name(first: _Run, second: _Run) -> None:
    assert sorted(first.files) == sorted(second.files)
    assert sorted(first.pdfs) == sorted(second.pdfs)


@pytest.mark.parametrize(
    "name",
    _params(
        [(name,) for name in _CSVS],
        {},
    ),
)
def test_a_rename_leaves_each_csv_byte_identical(first: _Run, second: _Run, name: str) -> None:
    assert _file(first, name) == _file(second, name)


def test_a_rename_leaves_the_overview_page_byte_identical(first: _Run, second: _Run) -> None:
    """A10: the page holds no Id, so a change of every Id changes no byte of it."""
    page = _file(first, "overview.html")
    assert not _ITEM_ID.search(page.decode())
    assert page == _file(second, "overview.html")


@pytest.mark.parametrize(
    ("pdf", "title"),
    _params(
        [(pdf, title) for pdf, titles in _PAGES.items() for title in titles],
        {},
    ),
)
def test_a_rename_leaves_each_pdf_page_text_identical(
    first: _Run, second: _Run, pdf: str, title: str
) -> None:
    a, b = _by_title(_pdf(first, pdf)), _by_title(_pdf(second, pdf))
    if title == "schematic":  # the draw order changes bytes, not the picture: compare positions
        assert [page.runs for page in a[title]] == [page.runs for page in b[title]]
    else:
        assert [page.text for page in a[title]] == [page.text for page in b[title]]


def test_a_rename_leaves_each_netlist_identical(first: _Run, second: _Run) -> None:
    assert first.netlists == second.netlists


def _overview_shapes(run: _Run) -> tuple[list[str], list[str]]:
    """Every overview box rectangle with its tabs, and every line's points, without any Id."""
    out = lay_out_overview(run.result.model)[0]
    boxes = [
        (b.x, b.y, b.width, b.height, b.dashed, tuple((t.x, t.y, t.text_width) for t in b.tabs))
        for b in layout_of(out, OverviewBox).values()
    ]
    lines = [
        (ln.kind, tuple((p.x, p.y) for p in ln.points), ln.text_x, ln.text_y)
        for ln in layout_of(out, OverviewLine).values()
    ]
    return sorted(map(repr, boxes)), sorted(map(repr, lines))


def test_a_rename_leaves_the_overview_positions_identical(first: _Run, second: _Run) -> None:
    """A10: the overview engine's boxes, tabs and lines do not read an Id's spelling."""
    shapes = _overview_shapes(first)
    assert shapes[0], "the canary system level holds boxes"
    assert shapes[1], "the canary's top-level cable is a line of the system level"
    assert shapes == _overview_shapes(second)


# ---- FT3: finding messages survive a rename -------------------------------------------------

_ANY_ID = re.compile(r"\b[a-z_]+:[0-9a-f]{32}\b")
_SUBJECT_KEY = re.compile(r"^(  subject: \S+:\d+) \(.*\)$", re.MULTILINE)
_VARIANT_CODES = {"PE_NOT_GNYE", "GNYE_NOT_PE", "STRIP_WITHOUT_TAG", "ITEM_WITHOUT_PART"}


def _variant(salt: str) -> fr.BuildResult:
    """The canary plus the smallest additions that raise the ERROR and part-conformance codes.

    A single wire on a PE net coloured RD (`PE_NOT_GNYE`), a GNYE wire on a non-PE net
    (`GNYE_NOT_PE`) and one floating strip with no terminals (`STRIP_WITHOUT_TAG`). The canary
    itself raises `ITEM_WITHOUT_PART`. An ERROR stops `fr.write`, so the variant is only built.
    """
    d, _ = _design(salt)
    lamps = [d.device(f"P{c}", "DEMO-LAMP-24", place="C1", name=f"{salt}p{c}") for c in "ABCD"]
    d.earth(lamps[0][1], lamps[1][1])
    d.wire(lamps[0][1], lamps[1][1], wire=(RD, 0.75))
    d.net("N1", lamps[2][1], lamps[3][1])
    d.wire(lamps[2][1], lamps[3][1], wire=(GNYE, 0.75))
    d.terminal_strip(None, "DEMO-TB-2.5", place="C1", name=f"{salt}bare")
    return fr.build(d)


def _plain(message: str) -> str:
    """A described message without the authoring key and the Id order of its subject lines.

    `describe` appends `file:line (key)` per subject, in `Id` order: the line stays, sorted; the
    key is the subject line's own and not message text (FT1).
    """
    head, *subjects = message.split("\n")
    return "\n".join([head, *sorted(_SUBJECT_KEY.sub(r"\1", line) for line in subjects)])


def _messages(result: fr.BuildResult) -> list[tuple[str, str]]:
    """Every `fr.check` finding as (code, message), in finding order."""
    return [(f.code, _plain(f.message)) for f in fr.check(result)]


@pytest.fixture(scope="module")
def variants() -> tuple[fr.BuildResult, fr.BuildResult]:
    return _variant("a-"), _variant("b-")


def test_the_variant_raises_each_code_the_message_test_needs(
    variants: tuple[fr.BuildResult, fr.BuildResult],
) -> None:
    for result in variants:
        assert {code for code, _ in _messages(result)} >= _VARIANT_CODES


def test_a_rename_leaves_every_finding_message_identical(
    first: _Run,
    second: _Run,
    variants: tuple[fr.BuildResult, fr.BuildResult],
) -> None:
    """FT1, FT3: a message names a thing as the drawings print it, so no key shows in it."""
    pairs = [(_messages(first.result), _messages(second.result)), tuple(map(_messages, variants))]
    for a, b in pairs:
        assert a, "the design raises findings"
        assert a == b
        assert not any(_ANY_ID.search(message) for _, message in a)
