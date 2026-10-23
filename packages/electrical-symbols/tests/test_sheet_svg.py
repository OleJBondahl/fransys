"""The sheet's SVG wrapper and the bold layer: the only markup the sheet adds to symdef's."""

import pytest

from electrical_symbols import bold_layer, sheet_svg

_BODY = '<g><line x1="0" y1="0" x2="1" y2="1"/></g>'


def test_a_sheet_is_an_svg_page_in_mm_with_its_body_inside():
    assert sheet_svg(420, 297, _BODY, margin_mm=0) == (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" '
        f'viewBox="0 0 420 297">{_BODY}</svg>'
    )


def test_the_bold_layer_wraps_its_fragment_in_a_bold_group():
    assert bold_layer(_BODY) == f'<g font-weight="bold">{_BODY}</g>'


def test_a_margin_shifts_the_view_box_and_widens_the_page_on_every_side():
    assert sheet_svg(10, 20, _BODY, margin_mm=0.125) == (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10.25mm" height="20.25mm" '
        f'viewBox="-0.125 -0.125 10.25 20.25">{_BODY}</svg>'
    )


def test_a_float_zero_margin_is_the_plain_page():
    assert sheet_svg(10.0, 20.0, _BODY, margin_mm=0.0) == sheet_svg(10.0, 20.0, _BODY, margin_mm=0)
    assert 'viewBox="0 0 10.0 20.0"' in sheet_svg(10.0, 20.0, _BODY, margin_mm=0.0)


def test_the_margin_is_required():
    with pytest.raises(TypeError):
        sheet_svg(10, 20, _BODY)  # ty: ignore[missing-argument] -- the margin is required
