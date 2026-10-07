"""Cable engine, the lower band as a channel: tracks for the bending cores (CT5-3 P2 ruling).

Integers only. Top terminals are the cores' box columns, bottom terminals their pins. Where a
column meets another core's pin the column's core runs above it; a cycle of such demands is
broken by a jog, and the tracks fill from the top, each by left edge then core key.
"""

from dataclasses import dataclass, replace
lazy from collections.abc import Collection, Mapping, Sequence
lazy from collections.abc import Set as AbstractSet

from fransys_layout.geometry import WIRING_GRID

G = WIRING_GRID
UPPER, LOWER = 1, 2  # the two halves of a jogged core


@dataclass(frozen=True, slots=True)
class Net:
    """One run of a bending core: a whole core (`part` 0) or one half of a jogged core."""

    core: int
    top: int
    bottom: int
    part: int = 0
    link: bool = False  # a row link (CD5 at L1): `top` and `bottom` are its two pins, both below

    @property
    def pins(self) -> tuple[int, ...]:
        """The columns of this net that stand on a pin of the bottom row."""
        return (self.top, self.bottom) if self.link else (self.bottom,)

    @property
    def left(self) -> int:
        return min(self.top, self.bottom)

    @property
    def right(self) -> int:
        return max(self.top, self.bottom)


@dataclass(frozen=True, slots=True)
class Plan:
    """The channel's answer: the nets (halves included), each one's track from 1, the count."""

    nets: tuple[Net, ...]
    tracks: tuple[int, ...]

    @property
    def count(self) -> int:
        return max(self.tracks, default=0)


def _above(nets: Sequence[Net]) -> dict[int, set[int]]:
    """Net index -> the nets that must run above it (they leave its pin column, or are its half)."""
    found: dict[int, set[int]] = {i: set() for i in range(len(nets))}
    for i, one in enumerate(nets):
        for j, other in enumerate(nets):
            if i == j:
                continue
            if one.core == other.core:
                if (one.part, other.part) == (UPPER, LOWER):
                    found[j].add(i)  # the first half's track runs above the second's
            elif not one.link and one.top in other.pins:
                found[j].add(i)
    return found


def _unplaced(above: Mapping[int, AbstractSet[int]]) -> set[int]:
    """The nets left once every net with nothing above it is peeled off: the cycles and below."""
    left = set(above)
    while free := {i for i in left if not left.intersection(above[i])}:
        left -= free
    return left


def _cycle(nets: Sequence[Net]) -> list[int] | None:
    """One cycle of the demands, found by walking up from the lowest net left; None if acyclic."""
    above = _above(nets)
    left = _unplaced(above)
    if not left:
        return None
    walk = [min(left)]
    while (prev := min(left.intersection(above[walk[-1]]))) not in walk:
        walk.append(prev)
    return walk[walk.index(prev) :]


def _jog_column(net: Net, taken: Collection[int]) -> int | None:
    """The free wiring column nearest `net`'s bottom pin, strictly between its two ends."""
    columns = range(net.left + G, net.right, G)
    free = [x for x in columns if x not in taken]
    return min(free, key=lambda x: (abs(x - net.bottom), x)) if free else None


def _split(
    nets: Sequence[Net], cycle: Sequence[int], taken: Collection[int]
) -> tuple[tuple[Net, ...], int] | None:
    """Jog the highest-keyed whole core of `cycle`: the nets with it halved, and its jog column."""
    whole = [i for i in cycle if nets[i].part == 0]
    if not whole:
        return None
    i = max(whole, key=lambda k: nets[k].core)
    column = _jog_column(nets[i], taken)
    if column is None:
        return None
    halves = (replace(nets[i], bottom=column, part=UPPER), replace(nets[i], top=column, part=LOWER))
    return (*nets[:i], *halves, *nets[i + 1 :]), column


def _one_track(
    nets: Sequence[Net], above: Mapping[int, AbstractSet[int]], done: AbstractSet[int]
) -> list[int]:
    """The nets one track takes: by left edge, then core key, apart and with their demands met."""
    order = sorted(
        (i for i in range(len(nets)) if i not in done),
        key=lambda i: (nets[i].left, nets[i].core, nets[i].part),
    )
    taken: list[int] = []
    for i in order:
        if above[i] <= done and (not taken or nets[i].left > nets[taken[-1]].right):
            taken.append(i)
    return taken


def _fill(nets: Sequence[Net]) -> tuple[int, ...] | None:
    """Tracks from the top, each filled before the next; None if a track takes nothing."""
    above = _above(nets)
    track: dict[int, int] = {}
    level = 0
    while len(track) < len(nets):
        level += 1
        taken = _one_track(nets, above, set(track))
        if not taken:
            return None
        track.update(dict.fromkeys(taken, level))
    return tuple(track[i] for i in range(len(nets)))


def plan_channel(
    columns: Sequence[tuple[int, int, int]], links: AbstractSet[int] = frozenset()
) -> Plan | None:
    """The tracks of the bending cores among `columns` (each core's key, top x, bottom x), or None.

    A straight core takes no track. A key in `links` is a row link: its two x are pins, and no net
    runs above it. Nets are sorted by core key, so the plan ignores the order of `columns`.
    """
    taken = {x for _, top, bottom in columns for x in (top, bottom)}
    bending = sorted((key, top, bottom) for key, top, bottom in columns if top != bottom)
    nets = tuple(Net(core=k, top=t, bottom=b, link=k in links) for k, t, b in bending)
    while (cycle := _cycle(nets)) is not None:
        split = _split(nets, cycle, taken)
        if split is None:
            return None
        nets = split[0]
        taken.add(split[1])
    tracks = _fill(nets)
    return None if tracks is None else Plan(nets=nets, tracks=tracks)


def rise(plan: Plan, level: int, head: int) -> int:
    """The height from the band top to track `level`: a grid unit a track, `head` more a link track.

    A link track has `head` more room above it, for the link's text (CD8 at L1).
    """
    linked = {t for net, t in zip(plan.nets, plan.tracks, strict=True) if net.link}
    return G * level + head * sum(1 for t in linked if t <= level)


def plan_links(spans: Sequence[tuple[int, int, int]]) -> tuple[int, ...]:
    """The upper band's track of each link (key, x, x), filled by left edge, then key."""
    nets = tuple(Net(core=k, top=a, bottom=b, link=True) for k, a, b in spans)
    return _fill(nets) or ()
