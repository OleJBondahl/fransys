"""The placement rules that read facts a scene carries: P1, P3 and P6 (design section 3.1).

A fact is a flag on a box or pin (`ScenePin.box`, `SceneBox.attached`, `.head` and `.strip`).
The rules read the flags and never ask what a symbol is.
"""

from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from .score_placement import _touching, _vertices

if TYPE_CHECKING:
    from .outputs import Scene, SceneBox

FAN = 3  # symbols on a net that make a fan


def attached_off_pin(scene: Scene) -> list[str]:
    """P1: a column hung on a box pin does not stand on that pin's page at its x, straight."""
    spots: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for b in scene.boxes:
        for p in b.pins:
            if p.box and p.net is not None:
                spots[p.net].add((b.page, p.x))
    ok: dict[tuple[str, str], bool] = {}
    for b in scene.boxes:
        for p in b.pins:
            if b.attached and p.net in spots:
                key = (b.sym, p.pin)
                ok[key] = ok.get(key, False) or (b.page, p.x) in spots[p.net]
    return sorted(f"{box}.{pin}" for (box, pin), good in ok.items() if not good)


def _legs(scene: Scene, net: str, skip: tuple[str, str]) -> Counter[int]:
    return Counter(
        b.page for b in scene.boxes for p in b.pins if p.net == net and (b.sym, p.pin) != skip
    )


def _fan_heads(scene: Scene) -> dict[tuple[str, str], tuple[str, set[int]]]:
    """Head pins on a net of 3+ symbols: (box id, pin) -> (net, the pages the head stands on)."""
    sizes: dict[str, set[str]] = defaultdict(set)
    for b in scene.boxes:
        for p in b.pins:
            if p.net is not None:
                sizes[p.net].add(b.sym)
    found: dict[tuple[str, str], tuple[str, set[int]]] = {}
    for b in scene.boxes:
        for p in b.pins:
            if b.head and p.net is not None and len(sizes[p.net]) >= FAN:
                found.setdefault((b.sym, p.pin), (p.net, set()))[1].add(b.page)
    return found


def head_off_legs(scene: Scene) -> list[str]:
    """P3: a fan head on a page that holds fewer of its legs than another page holds."""
    out = []
    for key, (net, mine) in _fan_heads(scene).items():
        legs = _legs(scene, net, key)
        if legs and max(legs[page] for page in mine) < max(legs.values()):
            out.append(f"{key[0]}.{key[1]}")
    return sorted(out)


def _end(box: SceneBox, vertices: frozenset[tuple[int, int, int]]) -> str | None:
    """`head` when the terminal's wire leaves downward, `foot` upward, else no end."""
    sides = {p.side for p in box.pins if (box.page, p.x, p.y) in vertices}
    if "S" in sides and "N" not in sides:
        return "head"
    return "foot" if "N" in sides and "S" not in sides else None


def row_broken(scene: Scene) -> list[str]:
    """P6: terminals of one strip at the same end of their columns on one page off a shared y."""
    vertices = _vertices(scene)
    groups: dict[tuple[str, int, str], list[SceneBox]] = defaultdict(list)
    for b in scene.boxes:
        end = _end(b, vertices) if b.strip is not None and _touching(b, vertices) else None
        if end is not None and b.strip is not None:
            groups[b.strip, b.page, end].append(b)
    out = []
    for members in groups.values():
        rows = Counter(b.body.y + b.body.h // 2 for b in members)
        modal = min(rows, key=lambda y: (-rows[y], y))
        out += [b.sym for b in members if b.body.y + b.body.h // 2 != modal]
    return sorted(out)
