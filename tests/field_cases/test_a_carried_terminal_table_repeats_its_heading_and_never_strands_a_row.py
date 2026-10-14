"""Field case: a terminal table carried to the next column keeps its heading and two rows a side.

The engineering shape: a cabinet with a long terminal strip and a second, shorter strip with a
one-line description, so the second strip's table meets the foot of the first column. The
list flows down 40 % columns, left then right.

The bug (v0.15): the second strip's heading and header row and one data row stood at the foot of
column 1, and its remaining rows stood in column 2 under a repeated header row but no heading.
Nothing told the reader whose rows they were, and one row hung alone at the foot. A table of
three rows split the same way.
The rule (decision pdf-0027): a table carried to the next column or page repeats its heading with
" (cont.)", a split leaves at least two data rows on each side, and a table of three rows or
fewer that does not fit moves whole.
"""

import re
lazy from pathlib import Path

import fransys as fr
import pypdfium2

_HEADING = re.compile(r"^-X(\d+)( \(cont\.\))?$")
_ROW = re.compile(r"^-X(\d+):\d+\b")


def _pdf(root: Path, counts: tuple[int, ...]) -> Path:
    """The cabinet's PDF: one strip per count, the later ones with a description; list only."""
    d = fr.design("demo_parts")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    for number, count in enumerate(counts, 1):
        note = "Valve feedback" if number > 1 else ""
        d.terminal_strip(f"X{number}", "DEMO-TB-2.5", count, place="C1", description=note)
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        cabinet,
        cover=cover,
        add=(fr.PageKind.TERMINAL_LIST,),
        remove=(fr.PageKind.SCHEMATIC,),
    )
    fr.write(fr.build(d, document), out_dir=root / "out", intermediates=root / "inter")
    (pdf,) = (root / "out").glob("*.pdf")
    return pdf


class _Fragment:
    """One strip's piece of one column: its data rows and the heading lines above them."""

    def __init__(self) -> None:
        self.rows = 0
        self.headings: list[str] = []


def _fragments(pdf: Path) -> dict[int, list[_Fragment]]:
    """Each strip's fragments in reading order: pages in turn, left column then right."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        found: dict[int, list[_Fragment]] = {}
        for page in document:
            text = page.get_textpage()
            full = text.get_text_range()
            if "Page title\r\nTerminal list" not in full:
                continue
            width, _ = page.get_size()
            places: dict[tuple[int, int], _Fragment] = {}
            at = 0
            for line in full.split("\r\n"):
                start = full.index(line, at) if line else at
                at = start + len(line)
                row, heading = _ROW.match(line), _HEADING.match(line)
                matched = row or heading
                if matched is None:
                    continue
                column = int(text.get_charbox(start)[0] > width / 2)
                strip = int(matched.group(1))
                piece = places.setdefault((column, strip), _Fragment())
                if row:
                    piece.rows += 1
                else:
                    piece.headings.append(line)
            for (_, strip), piece in sorted(places.items()):
                found.setdefault(strip, []).append(piece)
        return found
    finally:
        document.close()


def test_a_split_table_leaves_at_least_two_rows_on_each_side(tmp_path: Path) -> None:
    """Strips of 39 and 8 terminals: the second one splits 1 + 7 today."""
    fragments = _fragments(_pdf(tmp_path, (39, 8)))
    assert sum(piece.rows for piece in fragments[2]) == 8
    if len(fragments[2]) > 1:
        assert [piece.rows >= 2 for piece in fragments[2]] == [True] * len(fragments[2])


def test_a_carried_table_repeats_its_heading_with_cont(tmp_path: Path) -> None:
    """Strips of 30 and 20 terminals: the second splits, the first part plainly headed."""
    first, *carried = _fragments(_pdf(tmp_path, (30, 20)))[2]
    assert carried
    assert first.headings == ["-X2"]
    assert all(piece.headings == ["-X2 (cont.)"] for piece in carried)


def test_a_table_of_three_rows_that_does_not_fit_moves_whole(tmp_path: Path) -> None:
    """Strips of 39 and 3 terminals: the three rows split 1 + 2 today."""
    fragments = _fragments(_pdf(tmp_path, (39, 3)))
    assert [piece.rows for piece in fragments[2]] == [3]
