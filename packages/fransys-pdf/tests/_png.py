"""PNG decode and ink scanning, for R9's compiled-page checks (`test_frame_compiled.py`).

`typst.compile(..., format="png")` emits one 8-bit RGBA, non-interlaced PNG per page -- verified
against its own `IHDR` chunk (colour type 6, bit depth 8, interlace 0) before this module was
written. `decode_png` is built on `PIL.Image`, which replaced a pure-Python defilter/Paeth
decoder that used to live here: it dominated CPU time (70-97%) in the two slow compiled-page
tests at 600 ppi (see decision 0036).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image

_BPP = 4  # bytes per pixel: 8-bit RGBA, the only PNG shape `typst.compile` emits here


@dataclass(frozen=True)
class Raster:
    """A decoded PNG page: `width` x `height` pixels, 4 bytes (RGBA) each, row-major."""

    width: int
    height: int
    pixels: bytes

    def is_dark(self, x: int, y: int, *, threshold: int) -> bool:
        i = (y * self.width + x) * _BPP
        r, g, b = self.pixels[i], self.pixels[i + 1], self.pixels[i + 2]
        return (r + g + b) // 3 < threshold


@dataclass(frozen=True)
class Box:
    """A pixel-space rectangle `[x0,x1) x [y0,y1)` to scan for ink."""

    x0: int
    x1: int
    y0: int
    y1: int


def decode_png(data: bytes) -> Raster:
    """Decode one PNG page from `typst.compile(..., format="png")` (8-bit RGBA, no interlace)."""
    with Image.open(BytesIO(data)) as image:
        rgba = image if image.mode == "RGBA" else image.convert("RGBA")  # no extra full-page copy
        width, height = rgba.size
        pixels = rgba.tobytes()
    return Raster(width=width, height=height, pixels=pixels)


def ink_bbox(raster: Raster, box: Box, *, threshold: int = 200) -> tuple[int, int, int, int] | None:
    """The pixel bounding box of dark pixels in `box`, or `None` if none."""
    min_x = min_y = max_x = max_y = None
    for y in range(box.y0, box.y1):
        for x in range(box.x0, box.x1):
            if raster.is_dark(x, y, threshold=threshold):
                min_x = x if min_x is None else min(min_x, x)
                max_x = x if max_x is None else max(max_x, x)
                min_y = y if min_y is None else min(min_y, y)
                max_y = y if max_y is None else max(max_y, y)
    if min_x is None:
        return None
    assert min_y is not None
    assert max_x is not None
    assert max_y is not None
    return (min_x, min_y, max_x, max_y)


def horizontal_rules(
    raster: Raster, box: Box, *, threshold: int = 200, min_coverage: float = 0.9
) -> list[float]:
    """Row centres (in px) of `box` where dark pixels cover `min_coverage` of its width.

    A "rule" is a printed line spanning (almost) the whole span; running text never does --
    this is what tells a title-block rule apart from the label/value glyphs in the same cell.
    Adjacent dark rows are merged into one rule, its centre the mean of the merged rows.
    """
    span = box.x1 - box.x0
    dark_rows = []
    for y in range(box.y0, box.y1):
        dark = sum(1 for x in range(box.x0, box.x1) if raster.is_dark(x, y, threshold=threshold))
        if dark / span >= min_coverage:
            dark_rows.append(y)
    return _merge_runs(dark_rows)


def vertical_rules(
    raster: Raster, box: Box, *, threshold: int = 200, min_coverage: float = 0.9
) -> list[float]:
    """The column twin of `horizontal_rules`: column centres (in px) of full-height ink."""
    span = box.y1 - box.y0
    dark_cols = []
    for x in range(box.x0, box.x1):
        dark = sum(1 for y in range(box.y0, box.y1) if raster.is_dark(x, y, threshold=threshold))
        if dark / span >= min_coverage:
            dark_cols.append(x)
    return _merge_runs(dark_cols)


def _merge_runs(positions: list[int]) -> list[float]:
    if not positions:
        return []
    runs: list[float] = []
    start = prev = positions[0]
    for p in positions[1:]:
        if p == prev + 1:
            prev = p
        else:
            runs.append((start + prev) / 2)
            start = prev = p
    runs.append((start + prev) / 2)
    return runs
