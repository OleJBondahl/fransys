"""Authored layout kinds: rule parameters (design/layout-namespace.md, decision 0010).

Rule logic is engine code; every value a project can tune is a record here. Lengths of
a sheet are integer millimetres; everything the engine places is in grid units (`G`,
one eighth of the symbol module).
"""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, Value, make_id, record
from fransys_model.vocab.core import Unit


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


@record(kind="layout.profile")
class Profile:
    """The tunable numbers of the layout rules; at most one per unit and one for the top.

    `hide_unused_pins` hides, on drawings only, a box-drawn pin with no conductor. Text heights
    are the library's fixed heights, never a profile's. The layout numbers the drawings use are
    the `[profile]` table (`HouseProfile`, `tuning_of`). `unit` is the unit whose own drawings the
    profile governs, `None` for the top design's; `profile_of(model, unit)` returns that unit's
    authored profile, else `default_profile()`, never a containing unit's.
    """

    id: Id[Profile]
    key: AuthoringKey
    unit: Id[Unit] | None = None
    # On, a box-drawn pin with no conductor and a function with none are
    # not drawn; the lists keep every pin.
    hide_unused_pins: bool = False
    ext: frozendict[str, Value] = frozendict()


def default_profile() -> Profile:
    """The profile of a unit that authors none: every field at its class default, so none overrides the house.

    A constant of the model, not a record of any model; its id is fixed and is never put into a
    model. The house numbers are the `[profile]` table (`HouseProfile`), not this.
    """
    key = ("house", "profile")
    return Profile(id=make_id(Profile, key), key=key)
