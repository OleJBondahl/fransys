"""The record of the symbol library a build was drawn with: its grid and its font (GRID-HOME G6)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, record


@record(kind="layout.drawing_library", singleton=True)
class DrawingLibrary:
    """The grid and font numbers the drawings of one build share, written once by the facade.

    The facade fills it from the build's symbol library after `freeze()` and before any pass; an
    input never authors it. `module_mm` is one module and `divisions` its grid divisions (`G`).
    The pitches are in divisions. The three ratios are per font size (capital, ascent, descent).
    `heights` are capital heights in mm by name (`smallest`, `body`, `heading_2`, `heading_1`).
    Every conversion between grid units, millimetres and font sizes reads this record.
    """

    id: Id[DrawingLibrary]
    key: AuthoringKey
    module_mm: Decimal
    divisions: int
    wire_pitch: int
    wire_pitch_fine: int
    font_family: str
    capital_ratio: Decimal
    ascent_ratio: Decimal
    descent_ratio: Decimal
    heights: frozendict[str, Decimal]
    ext: frozendict[str, Value] = frozendict()
