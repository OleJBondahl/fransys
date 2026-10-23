"""The placement rules of the score that a scene alone can state, each kind-free.

`loose` is P5, `junction_off_line` P4, `pair_cut` P2 (design section 3.1). P1, P3 and P6 need
facts a scene does not carry yet (box pins, fan heads, strips), so they are not counted here.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .outputs import Scene, SceneBox, SceneWire

HUB = 3  # wires at a junction that make it a hub
PAIR = 2  # pins of a net that make a pair


def _vertices(scene: Scene) -> frozenset[tuple[int, int, int]]:
    return frozenset((w.page, x, y) for w in scene.wires for x, y in w.points)


def _straight(scene: Scene) -> frozenset[tuple[int, int, int]]:
    """Vertices of the polylines that stay on one x: a straight vertical wire's ends."""
    return frozenset(
        (w.page, x, y)
        for w in scene.wires
        if len({p[0] for p in w.points}) == 1
        for x, y in w.points
    )


def _touching(box: SceneBox, vertices: frozenset[tuple[int, int, int]]) -> list[str]:
    return [p.pin for p in box.pins if (box.page, p.x, p.y) in vertices]


def loose(scene: Scene) -> list[str]:
    """P5: a box no wire touches, with no biased end and no marker on any pin."""
    vertices = _vertices(scene)
    marked = {(m.box, m.pin) for m in scene.markers}
    return [
        b.sym
        for b in scene.boxes
        if not _touching(b, vertices)
        and not any(p.biased or (b.sym, p.pin) in marked for p in b.pins)
    ]


def _is_junction(box: SceneBox) -> bool:
    nodes = {p.node for p in box.pins}
    return len(box.pins) > 1 and len(nodes) == 1 and None not in nodes


def junction_off_line(scene: Scene) -> list[str]:
    """P4: a junction with no straight vertical wire through it, unless it is a hub of 3+ wires.

    A loose junction is P5's, so it is not counted twice.
    """
    vertices, straight, lone = _vertices(scene), _straight(scene), set(loose(scene))
    out = []
    for box in scene.boxes:
        if not _is_junction(box) or box.sym in lone:
            continue
        touching = _touching(box, vertices)
        on_line = any((box.page, p.x, p.y) in straight for p in box.pins if p.pin in touching)
        hub = sum(1 for w in scene.wires if w.page == box.page and _ends_on(w, box)) >= HUB
        if not on_line and not hub:
            out.append(box.sym)
    return out


def _ends_on(wire: SceneWire, box: SceneBox) -> bool:
    pins = {(p.x, p.y) for p in box.pins}
    return any(point in pins for point in wire.points)


def pair_cut(scene: Scene) -> list[str]:
    """P2: a net outside `rails` of exactly two drawn pins whose boxes stand on two pages."""
    ends: dict[str, list[int]] = defaultdict(list)
    for box in scene.boxes:
        for pin in box.pins:
            if pin.net is not None and pin.net not in scene.rails:
                ends[pin.net].append(box.page)
    return sorted(net for net, pages in ends.items() if len(pages) == PAIR and pages[0] != pages[1])
