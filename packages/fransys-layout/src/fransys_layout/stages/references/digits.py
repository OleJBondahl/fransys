"""Two independent digit counts per drawing set, `#n`'s and `p<sheet>`'s, each two at least.

`#n`'s digits come from the set's reference groups, counted from `references`' own decisions by
derive's `heads_group`; `p<sheet>`'s from its sheets. A run of several sets also sizes for the
forms of a place in another set: `p<set>.<page>` and the `+<location>` prefix (layout-0132).
"""

from collections import Counter
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple, Protocol

from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import heads_group
from fransys_model.kernel import value

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.stages.types import MarkerSide, PagePlan

    from .types import LocationPath, MarkerDecision, UnitPath


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
    """What one set's reference box is sized for: its digits and a place in another set.

    `other_sets` is a set number's digits and `prefix` the `+<location>` labels (layout-0132).
    """

    refs: int = 2
    sheets: int = 2
    other_sets: int = 0  # 0 for a run of one set: no place is in another
    prefix: tuple[str, ...] = ()
    more: int = 0  # digits of the largest ` +k` the set prints, 0 when none does


FLOOR = Digits()  # `#n` and `p<sheet>` are sized for two digits at least
MORE_FLOOR = 2  # a set that prints a ` +k` sizes it for two digits at least, as `#n` and `p<sheet>`


@value
class SetDigits:
    """One drawing set's two digit counts: `refs` for its `#n`, `sheets` for `p<sheet>`."""

    drawing_set: int
    refs: int
    sheets: int
    other_sets: int = 0
    prefix: tuple[str, ...] = ()
    more: int = 0

    @property
    def digits(self) -> Digits:
        """The sizing `reference_size` reads."""
        return Digits(self.refs, self.sheets, self.other_sets, self.prefix, self.more)


def _digit_widths(group_count: int, sheet_count: int) -> tuple[int, int]:
    """The digits of a set's highest `#n` and highest sheet, each two at least."""
    return max(FLOOR[0], len(str(group_count))), max(FLOOR[1], len(str(sheet_count)))


def _reference_groups(markers: Iterable[Grouped]) -> Counter[int]:
    """Each set's reference groups, by derive's `heads_group`; an off stub heads none."""
    # Derive passes `named=` (a hub of branches). A stage "off" is a pure stub: branches name only
    # a "ref" end, which heads its group here whatever its text, so `named` is False for every
    # "off"; test_no_branch_names_a_pure_off_stub proves it.
    return Counter(one.drawing_set for one in markers if heads_group(one.star, one.side.value))


def more_digits(markers: Iterable[MarkerDecision]) -> dict[int, int]:
    """Each set's digit count for its largest ` +k`, from its markers' `others`; 0 prints none."""
    widest: Counter[int] = Counter()
    for one in markers:
        widest[one.drawing_set] = max(widest[one.drawing_set], one.others)
    return {
        number: max(MORE_FLOOR, len(str(most))) if most else 0 for number, most in widest.items()
    }


def _widest_prefix(location_paths: Mapping[int, LocationPath]) -> tuple[str, ...]:
    """The longest `+<location>` labels a place prints: a whole path, so never too narrow."""
    paths = (tuple(label for _, label in path) for path in location_paths.values())
    return max(paths, key=lambda labels: text_width("".join(labels), height=8), default=())


def _subtrees(paths: Mapping[int, UnitPath]) -> dict[UnitPath, list[int]]:
    """Each unit path's subtree: the sets whose unit path starts with it (the top's is empty)."""
    found: dict[UnitPath, list[int]] = {}
    for number, path in paths.items():
        for depth in range(len(path) + 1):
            found.setdefault(path[:depth], []).append(number)
    return found


def set_digits(
    markers: Iterable[Grouped],
    plans: Iterable[PagePlan],
    location_paths: Mapping[int, LocationPath],
    unit_paths: Mapping[int, UnitPath] = MappingProxyType({}),
    more: Mapping[int, int] = MappingProxyType({}),
) -> tuple[SetDigits, ...]:
    """Every drawing set's `SetDigits`, from its reference groups and its sheets, by set.

    A set sizes its other-set forms from the sets of its own subtree only: those whose unit path
    starts with its own (UNIT-REF-BOX, layout-0132).
    """
    sheets = Counter(plan.drawing_set for plan in plans)
    groups = _reference_groups(markers)
    paths = {one: unit_paths.get(one, ()) for one in sheets}
    subtrees = _subtrees(paths)
    sized: dict[UnitPath, tuple[int, tuple[str, ...]]] = {}
    for path, mates in subtrees.items():
        other = len(str(max(mates))) if len(mates) > 1 else 0
        widest = _widest_prefix({n: location_paths[n] for n in mates if n in location_paths})
        sized[path] = (other, widest if other else ())
    found = []
    for one in sorted(sheets):
        other, prefix = sized[paths[one]]
        refs, pages = _digit_widths(groups[one], sheets[one])
        found.append(
            SetDigits(
                drawing_set=one,
                refs=refs,
                sheets=pages,
                other_sets=other,
                prefix=prefix,
                more=more.get(one, 0),
            )
        )
    return tuple(found)


def digits_by_set(
    plans: Iterable[PagePlan],
    location_paths: Mapping[int, LocationPath],
    unit_paths: Mapping[int, UnitPath],
) -> dict[int, Digits]:
    """Each set's box sizing before `place`, from its pages alone (no reference group yet)."""
    return {
        one.drawing_set: one.digits for one in set_digits((), plans, location_paths, unit_paths)
    }
