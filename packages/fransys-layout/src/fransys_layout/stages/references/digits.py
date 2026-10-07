"""S4: two independent digit counts per drawing set, `#n`'s and `p<sheet>`'s, each two at least.

`#n`'s digits come from the set's reference groups, counted from `references`' own decisions by
derive's `heads_group`; `p<sheet>`'s from its sheets. A run of several sets also sizes for the
forms of a place in another set: `p<set>.<page>` and the `+<location>` prefix (layout-0132).
"""

from collections import Counter
from typing import TYPE_CHECKING, NamedTuple, Protocol

from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import heads_group
from fransys_model.kernel import value

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.stages.types import MarkerSide, PagePlan

    from .types import LocationPath


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


class Digits(NamedTuple):
    """What one set's reference box is sized for: its digits and a place in another set (S4).

    `other_sets` is a set number's digits and `prefix` the `+<location>` labels (layout-0132).
    """

    refs: int = 2
    sheets: int = 2
    other_sets: int = 0  # 0 for a run of one set: no place is in another
    prefix: tuple[str, ...] = ()


FLOOR = Digits()  # S4: `#n` and `p<sheet>` are sized for two digits at least


@value
class SetDigits:
    """One drawing set's two digit counts (S4): `refs` for its `#n`, `sheets` for `p<sheet>`."""

    drawing_set: int
    refs: int
    sheets: int
    other_sets: int = 0
    prefix: tuple[str, ...] = ()

    @property
    def digits(self) -> Digits:
        """The sizing `reference_size` reads."""
        return Digits(self.refs, self.sheets, self.other_sets, self.prefix)


def _digit_widths(group_count: int, sheet_count: int) -> tuple[int, int]:
    """S4: the digits of a set's highest `#n` and highest sheet, each two at least."""
    return max(FLOOR[0], len(str(group_count))), max(FLOOR[1], len(str(sheet_count)))


def _reference_groups(markers: Iterable[Grouped]) -> Counter[int]:
    """S4: each set's reference groups, by derive's `heads_group`; an off stub heads none (D4)."""
    # Derive passes `named=` (a hub of branches). A stage "off" is a pure stub: branches name only
    # a "ref" end, which heads its group here whatever its text, so `named` is False for every
    # "off"; test_no_branch_names_a_pure_off_stub proves it.
    return Counter(one.drawing_set for one in markers if heads_group(one.star, one.side.value))


def _widest_prefix(location_paths: Mapping[int, LocationPath]) -> tuple[str, ...]:
    """The longest `+<location>` labels a place prints (U7): a whole path, so never too narrow."""
    paths = (tuple(label for _, label in path) for path in location_paths.values())
    return max(paths, key=lambda labels: text_width("".join(labels), height=8), default=())


def set_digits(
    markers: Iterable[Grouped],
    plans: Iterable[PagePlan],
    location_paths: Mapping[int, LocationPath],
) -> tuple[SetDigits, ...]:
    """S4: every drawing set's `SetDigits`, from its reference groups and its sheets, by set."""
    sheets = Counter(plan.drawing_set for plan in plans)
    groups = _reference_groups(markers)
    other = len(str(max(sheets))) if len(sheets) > 1 else 0
    prefix = _widest_prefix(location_paths) if other else ()
    found = []
    for one in sorted(sheets):
        refs, pages = _digit_widths(groups[one], sheets[one])
        found.append(
            SetDigits(drawing_set=one, refs=refs, sheets=pages, other_sets=other, prefix=prefix)
        )
    return tuple(found)
