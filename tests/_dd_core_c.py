"""Readers of the core path's Drawings for the terminal-in-two-sets tests (DEL-4 lane C1, fork C).

A Drawing carries no model id: a terminal is found by the TAG text it prints and the terminal
symbol nearest that text in x; a marker by the texts it prints, its star kind by its library key.
"""

from itertools import pairwise

from _drawn_pages import drawn_pages

from fransys_model.layout import DrawingSet, Page, layout_of

__all__ = ["beside", "in_own_set", "joined", "markers_of", "stands", "tags_by_set"]


def in_own_set(model, page) -> bool:
    """Whether `page` belongs to a unit's own drawing set (False: the top-level set)."""
    sets = layout_of(model, DrawingSet)
    return sets[layout_of(model, Page)[page].drawing_set].unit is not None


def stands(model, tag: str, key: str = "terminal") -> dict:
    """The (page id, symbol) of the `key` symbol nearest the TAG text `tag`, by set.

    The unit's own set is `True`, the top-level one `False`; a set without the tag is absent.
    """
    found: dict = {}
    for page, drawing in drawn_pages(model).items():
        texts = [t for t in drawing.texts if t.kind == "TAG" and t.text == tag]
        for text in texts:
            near = min(
                (s for s in drawing.symbols if s.key == key),
                key=lambda s, text=text: abs(s.x - text.box.x) + abs(s.y - text.box.y),
            )
            found.setdefault(in_own_set(model, page), []).append((page, near))
    return found


def tags_by_set(model, tag: str) -> dict:
    """How many times each set (True: a unit's own) prints the TAG text `tag`."""
    counts: dict = {}
    for page, drawing in drawn_pages(model).items():
        n = sum(t.kind == "TAG" and t.text == tag for t in drawing.texts)
        if n:
            counts[in_own_set(model, page)] = counts.get(in_own_set(model, page), 0) + n
    return counts


def beside(model, a: tuple, b: tuple, key: str = "terminal") -> bool:
    """Whether two (page, symbol) stand on one page at one y with no `key` symbol between."""
    (pa, sa), (pb, sb) = a, b
    if (pa, sa.y) != (pb, sb.y):
        return False
    low, high = sorted((sa.x, sb.x))
    between = [s for s in drawn_pages(model)[pa].symbols if s.key == key and low < s.x < high]
    return not between


def markers_of(model, tag: str, kind: str | None = None, page=None) -> list:
    """The (page id, marker) that print `tag` (and whose library key names `kind`), on `page`."""
    return [
        (p, m)
        for p, drawing in drawn_pages(model).items()
        for m in drawing.markers
        if (page is None or p == page)
        and (kind is None or kind in m.key)
        and any(tag in value for _, value in m.texts)
    ]


def _on(point, a, b) -> bool:
    (x, y), (x0, y0), (x1, y1) = point, a, b
    return min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)


def _segments(points) -> list:
    return list(pairwise(points))


def _touch(one, other) -> bool:
    """Whether two polylines (point tuples) meet."""
    return any(_on(p, *seg) for p in one for seg in _segments(other)) or any(
        _on(p, *seg) for p in other for seg in _segments(one)
    )


def joined(model, page, *pins: tuple[int, int]) -> bool:
    """Whether every pin point lies on one run of touching wires of `page`."""
    wires = [w.points for w in drawn_pages(model)[page].wires]
    runs: list[set[int]] = []
    for i, points in enumerate(wires):
        touching = [run for run in runs if any(_touch(points, wires[j]) for j in run)]
        runs = [*(run for run in runs if run not in touching), {i}.union(*touching)]
    return any(
        all(any(_on(pin, *seg) for j in run for seg in _segments(wires[j])) for pin in pins)
        for run in runs
    )
