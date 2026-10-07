"""HL21: each unit group's columns gathered into one packing unit, as wide as it folds.

Private to `stages.partition`. One pass over the units: a band column leaves its unit for its
group's, which stands at its first member's place (layout-0153, extending layout-0103 S10).
"""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from ._packing import Unit

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey


@dataclass(frozen=True, slots=True)
class Band:
    """One middle group's band columns, and its outline's width plus one column gap."""

    upper: frozenset[AuthoringKey]
    lower: frozenset[AuthoringKey]
    outline: int


@dataclass(frozen=True, slots=True)
class Bands:
    """The bands, each band column's band (the first naming it, HL20) and each band's root band."""

    bands: tuple[Band, ...] = ()
    band_of: Mapping[AuthoringKey, int] = field(default_factory=dict)
    root: tuple[int, ...] = ()
    of_root: Mapping[int, tuple[int, ...]] = field(default_factory=dict)


def gather(
    units: Sequence[Unit], owners: Bands, width_of: Mapping[AuthoringKey, int]
) -> list[Unit]:
    """Each band's columns as one unit at its first member's place, the rest left as they were.

    Two bands that share a column are one unit: they share a page (HL20).
    """
    if not owners.bands:
        return list(units)
    order: list[Unit | int] = []
    members: dict[int, list[Unit]] = {}
    for unit in units:
        rest = tuple(key for key in unit.columns if key not in owners.band_of)
        roots = (owners.root[owners.band_of[k]] for k in unit.columns if k in owners.band_of)
        for root in dict.fromkeys(roots):
            if root not in members:
                order.append(root)
            members.setdefault(root, []).append(unit)
        if rest:
            order.append(_kept(unit, rest, width_of))
    units_of = {root: _group(root, found, owners, width_of) for root, found in members.items()}
    return [units_of[one] if isinstance(one, int) else one for one in order]


def banded(bands: Sequence[Band]) -> Bands:
    """The first band naming each column keeps it; a band that meets an earlier one joins it."""
    band_of: dict[AuthoringKey, int] = {}
    root = {index: index for index in range(len(bands))}
    for index, band in enumerate(bands):
        for key in sorted(band.upper | band.lower):
            earlier = band_of.setdefault(key, index)
            if earlier != index:
                low = min(_find(root, earlier), _find(root, index))
                root[_find(root, earlier)] = root[_find(root, index)] = low
    roots = tuple(_find(root, index) for index in range(len(bands)))
    of_root: dict[int, tuple[int, ...]] = {}
    for index, found in enumerate(roots):
        of_root[found] = (*of_root.get(found, ()), index)
    return Bands(tuple(bands), band_of, roots, of_root)


def _find(root: Mapping[int, int], index: int) -> int:
    while root[index] != index:
        index = root[index]
    return index


def _kept(unit: Unit, rest: tuple[AuthoringKey, ...], width_of: Mapping[AuthoringKey, int]) -> Unit:
    """`unit` without its band columns."""
    if rest == unit.columns:
        return unit
    return replace(unit, columns=rest, width=sum(width_of[key] for key in rest))


def _group(
    root: int,
    members: Sequence[Unit],
    owners: Bands,
    width_of: Mapping[AuthoringKey, int],
) -> Unit:
    """One root's unit: its members' band columns in order, as wide as its bands fold."""
    keys = tuple(
        key
        for unit in members
        for key in unit.columns
        if key in owners.band_of and owners.root[owners.band_of[key]] == root
    )
    return Unit(
        groups=tuple(group for unit in members for group in unit.groups),
        columns=keys,
        width=_folded(keys, root, owners, width_of),
        break_before=any(unit.break_before for unit in members),
        role=members[0].role,
    )


def _folded(
    keys: Sequence[AuthoringKey], root: int, owners: Bands, width_of: Mapping[AuthoringKey, int]
) -> int:
    """The bands side by side, each folded: its wider band of the columns it keeps, or its outline.

    HL12: the bands stack about the outline; HL20: groups that share a column stand side by side.
    A band whose columns an earlier band kept still draws its outline.
    """
    sums = {index: [0, 0] for index in owners.of_root[root]}
    for key in keys:
        index = owners.band_of[key]
        sums[index][key in owners.bands[index].lower] += width_of[key]
    return sum(max(up, low, owners.bands[index].outline) for index, (up, low) in sums.items())
