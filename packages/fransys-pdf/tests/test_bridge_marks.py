"""The Bridge marks are placed images: a tick stays centred in auto-height rows of any height.

pdf draws no line (pdf-0049): each cell holds `image` pieces render drew, with `%` of the row's
own height for the lane's line and for the tick's centre. This compiles two rows of different
heights and finds each tick on the page, and checks the cell source holds no `line(`.
"""

import io
from itertools import pairwise

import fransys_pdf
import pytest
import typst
from fransys_pdf._bridge import bridge_cell_typst, bridge_geometry
from fransys_pdf._tables import table_source
from fransys_pdf._typst import literal
from PIL import Image

from fransys_model.derive import BridgePiece, bridge_piece_key, jumper_lanes

PPI = 200
_MM = PPI / 25.4
PIECES = {
    bridge_piece_key("line"): BridgePiece(
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="3mm" height="1mm" viewBox="0 0 3 1">'
        '<line x1="1.5" y1="0" x2="1.5" y2="1" stroke="#000" stroke-width="0.18"/></svg>',
        width_mm=3.0,
        height_mm=1.0,
    ),
    bridge_piece_key("tick"): BridgePiece(
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="2mm" height="1mm" viewBox="0 0 2 1">'
        '<line x1="0" y1="0.5" x2="2" y2="0.5" stroke="#000" stroke-width="0.18"/></svg>',
        width_mm=2.0,
        height_mm=1.0,
    ),
}


def _cells(groups: tuple[int | None, ...]) -> list[str]:
    return [
        bridge_cell_typst(marks, PIECES) for marks in bridge_geometry(groups, jumper_lanes(groups))
    ]


def _page(groups: tuple[int | None, ...], texts: list[str]) -> Image.Image:
    rows = [
        [f"text({literal(t)})" if "\n" not in t else _stack(t), c]
        for t, c in zip(texts, _cells(groups), strict=True)
    ]
    table = table_source(["1fr", "15mm"], ['text("A")', 'text("Bridge")'], rows)
    head = (
        '#set text(font: "DejaVu Sans", size: 3mm)\n'
        "#set page(width: 70mm, height: auto, margin: 5mm)\n"
    )
    source = f"{head}{table}\n"
    compiler = typst.Compiler(font_paths=[fransys_pdf.font_dir()], ignore_system_fonts=True)
    png = compiler.compile(input=source.encode(), format="png", ppi=PPI)
    assert isinstance(png, bytes)  # one page: the stub also allows a list or None
    return Image.open(io.BytesIO(png)).convert("L")


def _stack(text: str) -> str:
    return "stack(" + ", ".join(f"text({literal(line)})" for line in text.split("\n")) + ")"


def _dark_runs(image: Image.Image, x0: int, x1: int) -> list[tuple[int, int]]:
    """Per pixel row: the longest dark run inside columns `x0..x1`, as (y, length)."""
    runs = []
    pixels = image.tobytes()
    for y in range(image.height):
        best = run = 0
        for x in range(x0, x1):
            run = run + 1 if pixels[y * image.width + x] < 128 else 0
            best = max(best, run)
        runs.append((y, best))
    return runs


def test_a_tick_is_centred_in_auto_height_rows_of_different_heights() -> None:
    image = _page((1, 1), ["short", "a\nb\nc\nd"])
    width = image.width
    borders = [y for y, run in _dark_runs(image, 0, width) if run > width * 0.8]
    edges = [y for i, y in enumerate(borders) if i == 0 or y - borders[i - 1] > 2]
    column = (
        width - int(20 * _MM),
        width - int(5.5 * _MM),
    )  # the Bridge column, inside its borders
    ticks = [
        y for y, run in _dark_runs(image, *column) if run >= int(1.5 * _MM) and y not in borders
    ]
    body = list(pairwise(edges[1:]))
    heights = [bottom - top for top, bottom in body]
    assert heights[1] > heights[0] + 5 * _MM, heights
    assert len(ticks) >= 2
    for top, bottom in body:
        inside = [y for y in ticks if top < y < bottom]
        assert inside, (top, bottom, ticks)
        assert abs(sum(inside) / len(inside) - (top + bottom) / 2) <= 2


def test_the_cell_holds_images_and_no_line_of_its_own() -> None:
    for cell in _cells((1, 2, 1, 2)):
        assert "line(" not in cell
        assert "image(" in cell


def test_a_jumper_group_without_the_pieces_is_a_named_error() -> None:
    (marks, *_) = bridge_geometry((1, 1), jumper_lanes((1, 1)))
    with pytest.raises(KeyError, match="bridge_pieces"):
        bridge_cell_typst(marks, None)
