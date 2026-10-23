"""A sheet as one SVG document: the page wrapper and the title block's bold layer.

symdef draws a fragment with one weight of text and no page around it; the sheet's two remaining
pieces of markup live here, so the renderer only calls functions with values.
"""


def bold_layer(fragment: str) -> str:
    """A fragment whose text is drawn bold: the title block's `title` layer."""
    return f'<g font-weight="bold">{fragment}</g>'


def sheet_svg(width_mm: float, height_mm: float, body: str, *, margin_mm: float) -> str:
    """One sheet's SVG: `body`, drawn in mm, on a page `width_mm` by `height_mm`.

    A margin `m` widens the page by `m` on every side: the viewBox starts at `-m -m` and the
    width and height grow by `2m`. A margin of 0 gives the plain page, byte for byte.
    """
    if not margin_mm:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
            f'viewBox="0 0 {width_mm} {height_mm}">{body}</svg>'
        )
    wide, high = width_mm + 2 * margin_mm, height_mm + 2 * margin_mm
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{wide}mm" height="{high}mm" '
        f'viewBox="{-margin_mm} {-margin_mm} {wide} {high}">{body}</svg>'
    )
