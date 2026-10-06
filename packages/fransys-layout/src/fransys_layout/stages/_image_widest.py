"""The widest place text a contact image can carry: room for what render prints (RW9)."""

from typing import TYPE_CHECKING

from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import partner_position_text, row_letter

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .pagerun import PageInputs
    from .references.types import LocationPath
    from .types import LocationInfo, PagePlan, Profile, SheetFormat

type Cross = tuple[int, LocationPath]


def _partner_seats(pages: int, cross: Cross | None) -> list[tuple[int, int, LocationPath]]:
    """Every seat a partner can stand in: the reader's set, and with `cross` another set twice.

    Another set is seated once with the longest path (the prefix form) and once with the
    reader's own (the set-number form).
    """
    seats: list[tuple[int, int, LocationPath]] = [(1, page, ()) for page in range(1, pages + 1)]
    if cross:
        set_number, longest = cross
        for page in range(1, pages + 1):
            seats += [(set_number, page, longest), (set_number, page, ())]
    return seats


def widest_where(
    pages: int, sheet: SheetFormat, profile: Profile, cross: Cross | None = None
) -> str:
    """D7, LD5, RW9: the widest place text over pages 1 to `pages` and every cell of the sheet.

    `cross` is (the highest set number, the longest location path) of a model with several
    sets. Every text is `partner_position_text`'s, so a form it gains is measured here.
    """
    own = (1, 0, ())
    return max(
        (
            partner_position_text(own, seat, column, row_letter(row))
            for seat in _partner_seats(pages, cross)
            for column in range(1, 1 + sheet.frame_columns)
            for row in range(sheet.frame_rows)
        ),
        key=lambda text: text_width(text, height=profile.text_height),
    )


def set_paths(
    plans: Sequence[PagePlan], locations: Sequence[LocationInfo]
) -> Mapping[int, LocationPath]:
    """Each drawing set's location path, of every plan with a location."""
    label = {one.location: one.label for one in locations}
    path_of = {one.location: tuple((node, label[node]) for node in one.path) for one in locations}
    return {plan.drawing_set: path_of[plan.location] for plan in plans if plan.location}


def cross_form(plans: Sequence[PagePlan], paths: Mapping[int, LocationPath]) -> Cross | None:
    """`widest_where`'s `cross` for these plans; none while there is one drawing set."""
    sets = {plan.drawing_set for plan in plans}
    if len(sets) < 2:  # noqa: PLR2004 -- one set has no partner in another set
        return None
    longest = max(
        paths.values(), key=lambda path: len("".join(label for _, label in path)), default=()
    )
    return max(sets), longest


def widest_places(plans: tuple[PagePlan, ...], inputs: PageInputs) -> tuple[str, str]:
    """D7, RW9: the widest place text of a run for an image of one set, and of several."""
    cross = cross_form(plans, set_paths(plans, inputs.locations))
    pages = max((plan.number for plan in plans), default=1)
    return (
        widest_where(pages, inputs.sheet, inputs.profile),
        widest_where(pages, inputs.sheet, inputs.profile, cross),
    )
