"""One sheet-sized SVG with its drawing at the content box (render-0009, render-0027)."""


def sheet_svg(
    sheet_mm: tuple[object, object],
    content_xy_mm: tuple[object, object],
    body: str,
    prelude: str = "",
) -> str:
    """The `<svg>` of a whole sheet: `prelude`, then `body` translated to the content box."""
    (width, height), (x, y) = sheet_mm, content_xy_mm
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" '
        f'height="{height}mm" viewBox="0 0 {width} {height}">'
        f'{prelude}<g transform="translate({x} {y})">{body}</g></svg>'
    )
