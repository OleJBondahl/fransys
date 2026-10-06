"""S4: two independent digit counts per drawing set, `#n`'s and `p<sheet>`'s, each two at least.

`#n`'s digits come from the set's reference groups, counted from `references`' own decisions;
`p<sheet>`'s from its sheets. Derive numbers the placed markers (`drawing_text.reference_number`):
a test asserts, per set, that the count here equals derive's highest `#n`.
"""

from collections import Counter
from typing import TYPE_CHECKING, Protocol

from fransys_layout.stages.types import MarkerSide
from fransys_model.kernel import value

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages.types import PagePlan


class Grouped(Protocol):
    """A text as the group count reads it: its set, its `star` kind and its end of the cut."""

    @property
    def drawing_set(self) -> int:
        """The drawing set it stands in."""
        ...

    @property
    def star(self) -> str:
        """Its kind: `""`, `"ref"`, `"branch"` or `"off"`."""
        ...

    @property
    def side(self) -> MarkerSide:
        """The owner or user end of its cut."""
        ...


FLOOR = (2, 2)  # S4: `#n` and `p<sheet>` are sized for two digits at least


@value
class SetDigits:
    """One drawing set's two digit counts (S4): `refs` for its `#n`, `sheets` for `p<sheet>`."""

    drawing_set: int
    refs: int
    sheets: int


def _digit_widths(group_count: int, sheet_count: int) -> tuple[int, int]:
    """S4: the digits of a set's highest `#n` and highest sheet, each two at least."""
    return max(FLOOR[0], len(str(group_count))), max(FLOOR[1], len(str(sheet_count)))


def _reference_groups(markers: Iterable[Grouped]) -> Counter[int]:
    """S4: each set's reference groups: cut, star page-group, C17 split; an off stub none (D4)."""
    return Counter(
        one.drawing_set
        for one in markers
        if one.star == "ref" or (one.star in ("", "branch") and one.side is MarkerSide.OWNER)
    )


def set_digits(markers: Iterable[Grouped], plans: Iterable[PagePlan]) -> tuple[SetDigits, ...]:
    """S4: every drawing set's `SetDigits`, from its reference groups and its sheets, by set."""
    sheets = Counter(plan.drawing_set for plan in plans)
    groups = _reference_groups(markers)
    found = []
    for one in sorted(sheets):
        refs, pages = _digit_widths(groups[one], sheets[one])
        found.append(SetDigits(drawing_set=one, refs=refs, sheets=pages))
    return tuple(found)
