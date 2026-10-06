"""Authored layout kinds: rule parameters (design/layout-namespace.md, decision 0010).

Rule logic is engine code; every value a project can tune is a record here. Lengths of
a sheet are integer millimetres; everything the engine places is in grid units (`G`,
one eighth of the symbol module).
"""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, make_id, record


@record(kind="layout.sheet_format")
class SheetFormat:
    """A sheet: its size, the content box drawings may use, and the frame reference grid.

    Example: the invented A3 landscape format is 420 x 297 with a content box of
    400 x 257 at (10, 10), 8 frame columns and 6 frame rows, `module_mm=Decimal("2.5")`.
    The content box is in whole millimetres because a sheet is not a multiple of `G`.
    """

    id: Id[SheetFormat]
    key: AuthoringKey
    name: str
    width_mm: int
    height_mm: int
    content_x_mm: int
    content_y_mm: int
    content_width_mm: int
    content_height_mm: int
    frame_columns: int
    frame_rows: int
    module_mm: Decimal
    ext: frozendict[str, Value] = frozendict()


def default_sheet_format() -> SheetFormat:
    """The house sheet: A3 landscape, content 410 x 267 mm at (5, 5), 8 x 6 frame, 2.5 mm module.

    A constant of the model, not a record of any model: a derived `Page` with no
    `sheet_format` is drawn on it (design/layout-namespace.md), so the layout engine and an output
    module that draws the page frame read the same numbers and no pass has to write an authored
    kind. Its id is fixed and is never put into a model. The content box sits at (5, 5), not
    (10, 10): the owner's second appearance pass (spec page-frame R11.1, decision
    model-0051) halves the margin to 5 mm on every side, cutting in half the R10 default
    without narrowing the title-block band, which stays 20 mm between the bottom of the
    content box (`5 + 267 = 272`) and the frame's bottom edge (`297 - 5 = 292`).
    """
    key = ("house", "sheet")
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="A3 landscape",
        width_mm=420,
        height_mm=297,
        content_x_mm=5,
        content_y_mm=5,
        content_width_mm=410,
        content_height_mm=267,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )


@record(kind="layout.profile", singleton=True)
class Profile:
    """The tunable numbers of the layout rules; at most one per model.

    Gaps, `row_spacing`, `route_margin`, `text_height` and `marker_padding` are in `G`;
    penalties are unitless. `row_spacing` is the gap a column's next block keeps below the
    keep-out of the block before it. `marker_padding` is the clearance between a link
    marker's text and its outline, on every edge. `band_ranks` maps a `FunctionKind` value
    to the rank of its horizontal band, top first; `"terminal.first"` and `"terminal.last"`
    sit beside `"terminal"`. `group_ranks` maps the label of a `=` aspect node to its rank;
    an unranked group sorts last. `hide_unused_pins` hides, on drawings only, a box-drawn
    pin with no conductor. Every field defaults to its house value; a set field replaces it
    whole, a rank map is never merged. `profile_of(model)` returns the authored profile,
    else `default_profile()`.
    """

    id: Id[Profile]
    key: AuthoringKey
    # `None` is the house sheet (`default_sheet_format()`), which is no record.
    sheet_format: Id[SheetFormat] | None = None
    # Gaps in grid units G (1 M = 8 G): column gap 48, row gap 32. Pole pitch is the
    # symbol library's, not a tunable.
    column_gap: int = 48
    row_gap: int = 32
    row_spacing: int = 88
    route_margin: int = 64
    text_height: int = 8
    marker_padding: int = 2
    route_turn_penalty: int = 4
    route_crossing_penalty: int = 16
    # V1, CONVENTIONS-V06: on, a box-drawn pin with no conductor and a function with none are
    # not drawn; the lists keep every pin.
    hide_unused_pins: bool = False
    # Bands run top to bottom: supply and first terminal, protection, switching, overload
    # and measurement, load, last terminal. A terminal takes its band from its place in
    # the column (DESIGN 6.4).
    band_ranks: frozendict[str, int] = frozendict(
        {
            "supply": 0,
            "terminal.first": 0,
            "protection": 1,
            "switch": 2,
            "contact_no": 2,
            "contact_nc": 2,
            "contact_co": 2,
            "sensor": 3,
            "coil": 4,
            "load": 4,
            "actuator": 4,
            "terminal": 4,
            "terminal.last": 5,
        }
    )
    # No group ranks: a project states its own page order.
    group_ranks: frozendict[str, int] = frozendict()
    ext: frozendict[str, Value] = frozendict()


def default_profile() -> Profile:
    """The house profile: every field at its class default, used when a model authors none.

    A constant of the model, not a record of any model: a laid-out model with no
    authored `layout.profile` uses this (design/foundations.md 2.9 and design/vocabulary.md 7). Its
    id is fixed and is never put into a model. It takes no field arguments, so the house numbers
    have one home, the class's field defaults (decision model-0060). Its `sheet_format` is `None`,
    the house sheet.
    """
    key = ("house", "profile")
    return Profile(id=make_id(Profile, key), key=key)
