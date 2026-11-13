"""A region whose legs end on more than one open net is no two-terminal part: it is cut where its legs part (SP1, R2093).

SOURCE and SINK stand for one net each. The shared prefix is the region's series, and each leg after the
last node every leg shares is a region of its own, ending on its own net.
"""

from collections import defaultdict
lazy from collections.abc import Collection, Sequence

__all__ = ["cut", "root"]

type Raw = tuple[str, int | None, int | None]


def cut(raw: Sequence[Raw], stops: Collection[int]) -> list[list[Raw]]:
    """The region as parts that each end on one open net; the region itself when it already does.

    A leg's end on a hub (`stops`) is an open end of its own net; the start of a leg at a hub is no node.
    """
    legs = [(leaf, None if u in stops else u, v) for leaf, u, v in raw]
    original = {leg[0]: r for leg, r in zip(legs, raw, strict=True)}
    return [[original[leg[0]] for leg in part] for part in _cut(legs, stops)]


def _cut(legs: list[Raw], stops: Collection[int]) -> list[list[Raw]]:
    left = {u for _, u, _ in legs}
    if len({v for _, _, v in legs if v is None or v in stops or v not in left}) <= 1:  # one open net is a two-terminal part
        return [legs]
    node = _shared(legs, stops)
    if node is None:
        return [legs]
    before, after = _sides(legs, node)
    groups = _groups(after, node)
    if len(before) + len(after) != len(legs) or any(len(g) == len(legs) for g in groups):  # a loop, or no leg parts from another
        return [legs]
    return ([before] if before else []) + [part for group in groups for part in _cut(group, stops)]


def _open_reached(legs: Sequence[Raw], stops: Collection[int], blocked: int) -> bool:
    """Whether some open end is reached from a source along legs that avoid the node `blocked`."""
    entered = {v for _, _, v in legs}
    left = {u for _, u, _ in legs}
    seen: set[int | None] = set()
    todo = [u for _, u, _ in legs if u is None or u not in entered]
    while todo:
        here = todo.pop()
        if here in seen or here == blocked:
            continue
        seen.add(here)
        for _, u, v in legs:
            if u != here or v == blocked:
                continue
            if v is None or v in stops or v not in left:
                return True
            todo.append(v)
    return False


def _depth(legs: Sequence[Raw]) -> dict[int, int]:
    """Each node's fewest legs from a source."""
    entered = {v for _, _, v in legs}
    depth: dict[int, int] = {}
    layer = {u for _, u, _ in legs if u is None or u not in entered}
    level = 0
    while layer:
        depth.update({n: level for n in layer if n is not None and n not in depth})
        layer = {v for _, u, v in legs if u in layer and v is not None and v not in depth}
        level += 1
    return depth


def _shared(legs: Sequence[Raw], stops: Collection[int]) -> int | None:
    """The last node (an int) every path from a source to an open end passes, else `None`."""
    depth = _depth(legs)
    shared = [n for n in depth if not _open_reached(legs, stops, n)]
    return max(((depth[n], n) for n in shared), default=(0, None))[1]


def _reach(legs: Sequence[Raw], start: int, *, down: bool) -> set[int]:
    """The nodes from `start` along the legs (`down`) or against them, `start` included."""
    nexts: dict[int, set[int]] = defaultdict(set)
    for _, u, v in legs:
        if u is not None and v is not None:
            (nexts[u] if down else nexts[v]).add(v if down else u)
    seen, todo = {start}, [start]
    while todo:
        for n in nexts[todo.pop()] - seen:
            seen.add(n)
            todo.append(n)
    return seen


def _sides(legs: Sequence[Raw], node: int) -> tuple[list[Raw], list[Raw]]:
    """The legs that end at `node` or lead to it, and the legs that leave it or follow."""
    above, below = _reach(legs, node, down=False), _reach(legs, node, down=True)
    return [r for r in legs if r[2] in above], [r for r in legs if r[1] in below]


def root[T](parent: dict[T, T], x: T) -> T:
    """The representative of `x` in a union-find `parent` map."""
    while parent.get(x, x) != x:
        x = parent[x]
    return x


def _groups(legs: Sequence[Raw], node: int) -> list[list[Raw]]:
    """The legs after `node`, one group per set the legs join by a node other than `node`."""
    parent: dict[object, object] = {}
    for i, (_, u, v) in enumerate(legs):
        for end in (u, v):
            if end is not None and end != node:
                parent[root(parent, end)] = root(parent, ("leg", i))
    groups: dict[object, list[Raw]] = defaultdict(list)
    for i, leg in enumerate(legs):
        groups[root(parent, ("leg", i))].append(leg)
    return list(groups.values())
