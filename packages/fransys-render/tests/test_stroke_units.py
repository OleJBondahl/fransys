"""PART C: every length this package writes, past the root `<svg>` tag, is a bare number.

`_style.py`'s CSS `stroke-width`/`stroke-dasharray` used to carry an explicit `mm` suffix,
a CSS absolute length -- unlike every coordinate and `font-size` attribute this package
emits (PART 7), which are already bare numbers against this SVG's own `viewBox` (1 user
unit equals 1 mm, D5). A CSS absolute length is not read against that scale, so it compiled
to a different, wrong physical size (`docs/decisions/render-0001-...md`'s stroke-width
finding). Checked over all three real goldens this repo carries, the one place `pages()`
draws every real content shape it can draw, not just a hand-built case.
"""

import re

from fransys_render import pages

# The root `<svg width="...mm" height="...mm" viewBox="...">` legitimately carries `mm`:
# it is the page's own physical size, the fact that gives every OTHER coordinate its
# 1-user-unit-equals-1-mm meaning (D5) -- so this test scans everything AFTER that one
# opening tag, never the tag itself. Every CSS absolute length unit (CSS Values and Units,
# section 6.2), not just the `mm`/`px`/`pt` PART C actually found: `cm`, `in`, `pc`, `Q` are
# just as wrong here, for the same reason, if this package -- or a later change to it --
# ever wrote one.
_UNIT_LENGTH = re.compile(r"[0-9](mm|cm|in|pc|pt|px|Q)\b")

# A length declaration must actually be present to check -- otherwise an empty scan would
# pass vacuously and prove nothing (root CLAUDE.md: a loop asserts a non-zero count first).
_LENGTH_DECLARATION = re.compile(r"stroke-width|stroke-dasharray|font-size")
_MIN_PAGES_EXAMINED = 1
_MIN_LENGTH_DECLARATIONS = 1


def test_no_length_after_the_root_svg_tag_carries_a_css_absolute_unit(
    cabinet_laid_out, cabinet_narrow_laid_out, cabinet_two_location_laid_out
):
    pages_examined = 0
    declarations_found = 0
    for model in (cabinet_laid_out, cabinet_narrow_laid_out, cabinet_two_location_laid_out):
        for svg in pages(model).values():
            pages_examined += 1
            _root_tag, body = svg.split(">", 1)
            declarations_found += len(_LENGTH_DECLARATION.findall(body))
            assert _UNIT_LENGTH.search(body) is None, (model, svg)

    assert pages_examined >= _MIN_PAGES_EXAMINED
    assert declarations_found >= _MIN_LENGTH_DECLARATIONS
