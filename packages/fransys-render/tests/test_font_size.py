"""D7 bug fix: every `<text>` element this package draws carries a `font-size` (mm, unitless).

Before this fix, `_labels.py`, `_markers.py`'s `text_glyph` and `_symbols.py` all computed
`font_size_mm` for the baseline offset only -- no `<text>` element ever carried a `font-size`
attribute, so Typst's SVG renderer (usvg) fell back to its own default (~16 user units),
roughly 6.4x the intended size on the house sheet. Checked over both real goldens
(`cabinet_laid_out`, `cabinet_narrow_laid_out`), the one place this package's `pages()` draws
every real content shape (symbols, markers, labels) it can draw, not just a hand-built case.
"""

import xml.etree.ElementTree as ET

from fransys_render import pages
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.kernel.ids import render_id
from fransys_model.layout import Page, layout_of, profile_of, sheet_format_of

_SVG_NS = "{http://www.w3.org/2000/svg}"

# At least one `<text>` element must be found across both goldens before any of them are
# checked (root CLAUDE.md: a loop over records asserts a non-zero count first) -- otherwise
# an empty loop would pass vacuously and prove nothing.
_MIN_TEXT_ELEMENT_COUNT = 1


def _expected_font_size(model, page):
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of(model)
    return format_decimal(grid_to_mm(0, profile.text_height, sheet.module_mm))


def _text_elements_by_page(model):
    """Every `<text>` element of `model`'s rendered pages, paired with its own `Page` record."""
    svgs = pages(model)
    pages_by_key = {render_id(page.id): page for page in layout_of(model, Page).values()}
    pairs = []
    for key, svg in svgs.items():
        page = pages_by_key[key]
        root = ET.fromstring(svg)  # noqa: S314 -- parsing this package's own generated SVG
        pairs.extend((page, text_element) for text_element in root.findall(f".//{_SVG_NS}text"))
    return pairs


def test_every_text_element_carries_the_profiles_font_size(
    cabinet_laid_out, cabinet_narrow_laid_out
):
    pairs = []
    for model in (cabinet_laid_out, cabinet_narrow_laid_out):
        for page, text_element in _text_elements_by_page(model):
            pairs.append((model, page, text_element))

    assert len(pairs) >= _MIN_TEXT_ELEMENT_COUNT, "no <text> element found to check"

    for model, page, text_element in pairs:
        expected = _expected_font_size(model, page)
        assert text_element.attrib.get("font-size") == expected, (
            render_id(page.id),
            text_element.attrib,
            expected,
        )
