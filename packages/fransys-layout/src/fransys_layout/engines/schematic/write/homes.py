"""Where the run that owns a port draws it, for the cross-references of another run (model-0192)."""

from typing import TYPE_CHECKING, Any, NamedTuple

from fransys_model.layout import DrawingSet, Label, Page, layout_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.kernel import Id, Model, Record


class Homes(NamedTuple):
    """Run 0 is the base, run `i + 1` the `i`th unit run; ids are each run's own."""

    owner: dict[Id[Any], tuple[int, frozenset[Id[Page]]]]  # label -> its run, the pages it owns
    drawn: dict[tuple[int, Id[Any]], tuple[Id[Page], int]]  # (run, port) -> page, x
    run_of: list[dict[Id[Page], int]]  # per run: page -> the run that owns its unit


def _page_runs(laid: Model, unit_run: Mapping[Id[Any], int]) -> dict[Id[Page], int]:
    """Each page of `laid` and the run that owns the unit of its drawing set."""
    unit = {one.id: one.unit for one in layout_of(laid, DrawingSet).values()}
    return {
        one.id: unit_run.get(unit[one.drawing_set], 0) for one in layout_of(laid, Page).values()
    }


def drawn_by(
    base: Model,
    gone: Mapping[Id[Any], Record],
    runs: Iterable[tuple[frozenset[Id[Any]], Model]],
    parts: Iterable[Mapping[Id[Any], Record]],
) -> Homes:
    """Per label, its run and the pages that run owns; per (run, port), where that run draws it.

    The base run owns the pages its units' sets do not; a unit run, its own sets' pages. A run's
    labels on pages it drops still name the ports of the pages it keeps.
    """
    runs = list(runs)
    unit_run = {unit: i + 1 for i, (units, _) in enumerate(runs) for unit in units}
    kept = frozenset(one.id for one in layout_of(base, Page).values() if one.id not in gone)
    sources = [(base, kept, layout_of(base, Label).values())]
    for (_, laid), part in zip(runs, parts, strict=True):
        own = frozenset(i for i, one in part.items() if isinstance(one, Page))
        sources.append((laid, own, [one for one in part.values() if isinstance(one, Label)]))
    found = Homes({}, {}, [_page_runs(laid, unit_run) for laid, _, _ in sources])
    for i, (laid, own, labels) in enumerate(sources):
        found.owner.update((one.id, (i, own)) for one in labels)
        for one in layout_of(laid, Label).values():
            for end in one.partners:
                if end.page in own:
                    found.drawn.setdefault((i, end.port), (end.page, end.x))
    return found
