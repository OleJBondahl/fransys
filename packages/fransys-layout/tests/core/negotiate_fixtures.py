"""Seeded pages for the negotiated router: links across a wall with one or two gaps in it."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from itertools import count
from typing import TYPE_CHECKING

from fransys_layout.core import Box
from fransys_layout.core.clearance import Keep
from fransys_layout.core.route import _grid
from fransys_layout.core.route_tree import mark_anchors, tree

from .route_fixtures import link_env

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_layout.core.occupancy import Occupancy
    from fransys_layout.core.route_env import RouteEnv

Pins = dict[str, tuple[int, int, str]]
Links = dict[str, tuple[str, ...]]
WALL = 10  # the wall's column
Scene = tuple["RouteEnv", "Callable[[], Occupancy]"]


def _wall(grid: Occupancy, gaps: tuple[int, ...]) -> list[Box]:
    """The wall's boxes: column WALL top to bottom but for the rows `gaps`."""
    boxes: list[Box] = []
    top = 0
    for row in (*gaps, grid.rows):
        if row > top:
            boxes.append(Box(WALL * grid.step, top * grid.step, grid.step, (row - top) * grid.step))
        top = row + 1
    return boxes


def wall_scene(
    pins: Mapping[str, tuple[int, int, str]],
    links: Mapping[str, tuple[str, ...]],
    gaps: tuple[int, ...],
) -> Scene:
    """A page with a wall at column WALL, open at the rows `gaps`; the maker returns a fresh map."""
    env = link_env(pins, links)
    boxes = _wall(_grid(env, ()), gaps)

    def fresh() -> Occupancy:
        grid = _grid(env, ())
        for box in boxes:
            grid.mark_box(box)
        for link in env.cross_links:
            mark_anchors(env, grid, link)
        return grid

    return env, fresh


def walled_page(env: RouteEnv, gaps: tuple[int, ...]) -> RouteEnv:
    """The same page with the wall as obstacles, so `route_page` meets it."""
    keeps = tuple(Keep("", box, "wall", "") for box in _wall(_grid(env, ()), gaps))
    return replace(env, obstacles=keeps)


class Draws:
    """Numbers from a seed by hashing: the same seed always gives the same page."""

    def __init__(self, seed: int) -> None:
        self._seed, self._n = seed, count()

    def below(self, lo: int, hi: int) -> int:
        digest = hashlib.sha256(f"{self._seed}:{next(self._n)}".encode()).digest()
        return lo + int.from_bytes(digest[:4]) % (hi - lo)


def _gaps(r: Draws) -> tuple[int, ...]:
    """One or two distinct gap rows."""
    first = r.below(1, 11)
    second = r.below(1, 11)
    return (first,) if r.below(0, 2) or second == first else tuple(sorted((first, second)))


def _drawn(seed: int, names: Mapping[str, str] | None) -> tuple[Pins, Links, tuple[int, ...]]:
    """The pins, links and wall gaps of a seed."""
    r = Draws(seed)
    pins: dict[str, tuple[int, int, str]] = {}
    links: dict[str, tuple[str, ...]] = {}
    taken: set[tuple[int, int]] = set()
    for k in range(r.below(2, 4)):
        for e, (lo, hi, side) in enumerate(((2, 9, "E"), (12, 19, "W"))):
            c = (r.below(lo, hi), r.below(2, 10))
            while any(abs(c[0] - u[0]) <= 1 and abs(c[1] - u[1]) <= 1 for u in taken):
                c = (r.below(lo, hi), r.below(2, 10))
            taken.add(c)
            pins[f"s{k}{e}"] = (c[0] * 8, c[1] * 8, side)
        links[(names or {}).get(f"n{k}", f"n{k}")] = (f"s{k}0", f"s{k}1")
    return pins, links, _gaps(r)


def seeded_scene(seed: int, names: Mapping[str, str] | None = None) -> Scene:
    """Two or three links n0, n1, ... (or as `names` renames them) across a wall with 1-2 gaps."""
    return wall_scene(*_drawn(seed, names))


def seeded_page(seed: int) -> RouteEnv:
    """The seed's page for `route_page`: the same wall, as obstacles."""
    pins, links, gaps = _drawn(seed, None)
    return walled_page(link_env(pins, links), gaps)


def sequential_failures(scene: Scene) -> int:
    """Links routed one after the other, each hard, in place order: how many find no route."""
    env, fresh = scene
    grid, failed = fresh(), 0
    for link in env.cross_links:
        if tree(env, grid, link) is None:
            grid.remove_net(link.net)
            failed += 1
    return failed
