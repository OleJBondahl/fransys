"""A sheet as one SVG document: the page wrapper and the title block's bold layer.

symdef draws a fragment with one weight of text and no page around it; the sheet's two remaining
pieces of markup live here, so the renderer only calls functions with values.
"""


def bold_layer(fragment: str) -> str:
    """A fragment whose text is drawn bold: the title block's `title` layer."""
    return f'<g font-weight="bold">{fragment}</g>'


def sheet_svg(width_mm: float, height_mm: float, body: str) -> str:
    """One sheet's SVG: `body`, drawn in mm, on a page `width_mm` by `height_mm`."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">{body}</svg>'
    )
