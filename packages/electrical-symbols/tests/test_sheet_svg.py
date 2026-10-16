"""The sheet's SVG wrapper and the bold layer: the only markup the sheet adds to symdef's."""

from electrical_symbols import bold_layer, sheet_svg

_BODY = '<g><line x1="0" y1="0" x2="1" y2="1"/></g>'


def test_a_sheet_is_an_svg_page_in_mm_with_its_body_inside():
    assert sheet_svg(420, 297, _BODY) == (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" '
        f'viewBox="0 0 420 297">{_BODY}</svg>'
    )


def test_the_bold_layer_wraps_its_fragment_in_a_bold_group():
    assert bold_layer(_BODY) == f'<g font-weight="bold">{_BODY}</g>'
