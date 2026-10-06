"""Stub check (gap G18): the mate of the harness plug `-W3-J2` shows on a cabinet page.

The harness `-W3` ends in a plug `-W3-J2`, whose mate is the port on the switch `+EXT-K1`. Before
Schematika v0.3.0 that mate showed in no export. Since v0.3.0 (layout deep dive D10, the stubs)
the cabinet page that carries the wires of `-W3` writes a stub: the text
`-W3 ← +EXT-K1:1 2 3 4 5 6 7 8`, the harness, an arrow, then the mate and its ports.

The check reads `cabinet.typ`, the Typst source the cabinet PDF is compiled from, in the intermediates
directory of the `built` fixture: the PDF compresses its page content, while the `.typ` embeds each
layout page's SVG verbatim, so the stub text is plain text there. Pages are split at `#pagebreak()`.
The stub's page is found by its sheet title, `WAGO PLC` (written in the title block as the
`Page title` cell), not by a page number, so a page added or moved before it does not break the check.

The board document (`relay-board.typ`) has no harness, so it must not carry the stub.
"""

from pathlib import Path

import fransys as fr
import pytest

STUB_TEXT = "-W3 ← +EXT-K1:1 2 3 4 5 6 7 8"
STUB_TITLE = 'text(size: 10pt, text("WAGO PLC"))'
PAGE_BREAK = "#pagebreak()"


def stub_pages(typ_text: str) -> list[int]:
    """The 1-based page numbers (chunks between `#pagebreak()`) whose text holds the stub."""
    pages = typ_text.split(PAGE_BREAK)
    return [number for number, page in enumerate(pages, start=1) if f">{STUB_TEXT}</text>" in page]


def assert_stub_present(typ_text: str) -> None:
    """Assert the stub is on exactly one page, and that page's sheet title is `WAGO PLC`."""
    found = stub_pages(typ_text)
    assert len(found) == 1, f"stub {STUB_TEXT!r} is on pages {found}, not on exactly one"
    assert STUB_TITLE in typ_text.split(PAGE_BREAK)[found[0] - 1], (
        f"the stub's page {found[0]} is not the sheet titled 'WAGO PLC'"
    )


def test_stub_shows_on_the_cabinet_wago_plc_page(built: tuple[fr.BuildResult, Path, Path]) -> None:
    """G18: the stub of `-W3` towards `+EXT-K1` is on the cabinet page titled `WAGO PLC`."""
    _, _, intermediates = built
    assert_stub_present((intermediates / "cabinet.typ").read_text(encoding="utf-8"))


def test_stub_check_fails_when_the_stub_text_is_removed(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """Can-fail proof: the same check raises on a copy of the real text without the stub."""
    _, _, intermediates = built
    real_text = (intermediates / "cabinet.typ").read_text(encoding="utf-8")
    assert STUB_TEXT in real_text
    with pytest.raises(AssertionError):
        assert_stub_present(real_text.replace(STUB_TEXT, "-W3"))


def test_stub_check_fails_when_the_stub_is_not_on_the_wago_plc_page(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """Can-fail proof: the same check raises when the sheet title is not `WAGO PLC`."""
    _, _, intermediates = built
    real_text = (intermediates / "cabinet.typ").read_text(encoding="utf-8")
    assert STUB_TITLE in real_text
    with pytest.raises(AssertionError):
        assert_stub_present(real_text.replace(STUB_TITLE, 'text(size: 10pt, text("OTHER"))'))


def test_stub_is_absent_from_the_board_document(built: tuple[fr.BuildResult, Path, Path]) -> None:
    """The relay board document, made from the same build, has no stub for `-W3`."""
    _, _, intermediates = built
    board_text = (intermediates / "relay-board.typ").read_text(encoding="utf-8")
    assert stub_pages(board_text) == []
    assert "+EXT-K1" not in board_text
