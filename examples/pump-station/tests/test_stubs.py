"""Stub check (gap G18): the end of the cable `-W3` at the switch `+EXT-K1` shows on a cabinet page.

The cable `-W3` runs from the controller's port `-U1-C1-X1` to the port on the switch `+EXT-K1`.
The cabinet page that carries the wires of `-W3` writes a stub (layout deep dive D10): the text
`-W3 ← +EXT-K1`, the cable, an arrow, then the far end and its ports.

The check reads `pump-cabinet-v1.10.typ`, the Typst source the cabinet PDF is compiled from, in the intermediates
directory of the `built` fixture: the PDF compresses its page content, while the `.typ` embeds each
layout page's SVG verbatim, so the stub text is plain text there. Pages are split at `#pagebreak()`.
The stub's page is found by its sheet title (the title block's `Page title` cell lists the page's
functions, here `Incoming supply, Pump 1, Pump 2, WAGO PLC`), which must name `WAGO PLC`, not by a
page number, so a page added or moved before it does not break the check.
"""

import re
from pathlib import Path

import fransys as fr
import pytest

STUB_TEXT = "-W3 ← +EXT-K1"
STUB_TITLE = re.compile(
    r'<text x=\\"175\\" y=\\"289.625\\" font-size=\\"3.4293\\"[^>]*>([^<]*\bWAGO PLC\b[^<]*)</text>'
)  # the title block's sheet title: the page's functions, comma separated
PAGE_BREAK = "#pagebreak()"


def stub_pages(typ_text: str) -> list[int]:
    """The 1-based page numbers (chunks between `#pagebreak()`) whose text holds the stub."""
    pages = typ_text.split(PAGE_BREAK)
    return [number for number, page in enumerate(pages, start=1) if f">{STUB_TEXT}</text>" in page]


def assert_stub_present(typ_text: str) -> None:
    """Assert the stub is on exactly one page, and that page's sheet title is `WAGO PLC`."""
    found = stub_pages(typ_text)
    assert len(found) == 1, f"stub {STUB_TEXT!r} is on pages {found}, not on exactly one"
    assert STUB_TITLE.search(typ_text.split(PAGE_BREAK)[found[0] - 1]), (
        f"the stub's page {found[0]} is not a sheet titled with 'WAGO PLC'"
    )


def test_stub_shows_on_the_cabinet_wago_plc_page(built: tuple[fr.BuildResult, Path, Path]) -> None:
    """G18: the stub of `-W3` from `+EXT-K1` is on the cabinet page titled `WAGO PLC`."""
    _, _, intermediates = built
    assert_stub_present((intermediates / "pump-cabinet-v1.10.typ").read_text(encoding="utf-8"))


def test_stub_check_fails_when_the_stub_text_is_removed(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """Can-fail proof: the same check raises on a copy of the real text without the stub."""
    _, _, intermediates = built
    real_text = (intermediates / "pump-cabinet-v1.10.typ").read_text(encoding="utf-8")
    assert STUB_TEXT in real_text
    with pytest.raises(AssertionError):
        assert_stub_present(real_text.replace(STUB_TEXT, "-W3"))


def test_stub_check_fails_when_the_stub_is_not_on_the_wago_plc_page(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """Can-fail proof: the same check raises when the sheet title is not `WAGO PLC`."""
    _, _, intermediates = built
    real_text = (intermediates / "pump-cabinet-v1.10.typ").read_text(encoding="utf-8")
    assert STUB_TITLE.search(real_text)
    with pytest.raises(AssertionError):
        assert_stub_present(real_text.replace("WAGO PLC", "OTHER"))
