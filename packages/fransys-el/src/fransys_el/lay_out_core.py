"""`lay_out`: the core path, one drawing set per (unit, location) (PAGE-02, Rulings 50 and 70)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CoreError, PinRef, solve

from .draw_layout import finish_drawings
from .draw_write import ORIGIN, write_layout_drawn
from .drawn_netlist import drawn_netlist
from .drawn_sweep import drawing_sweep
from .placement_kit import ProblemError, refuse
from .placement_markers import facing_views, marker_fit
from .placement_options import options
from .placement_sets import drawing_scopes, restrict
from .placement_widest import link_fit
from .set_findings import cut_net_findings, set_failure_finding, set_without_page_findings
from .write import write_layout
from .write_pages import SetPlace

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Options, PlacementProblem
    from fransys_layout.drawing import Drawing
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import LinkMarker, Page

    from .placement_kit import SymbolKit
    from .placement_options import Conventions
    from .placement_sets import DrawingScope

__all__ = ["lay_out", "lay_out_drawn"]

# KeyError and IndexError are core faults that today escape `solve`; one set's fault must not
# hide the sets that lay out (FLIP-NOW F2), so they are findings too until the core names them.
_SET_FAILURES = (CoreError, ProblemError, KeyError, IndexError)


@dataclass(frozen=True)
class _Sink:
    """What `lay_out_drawn` collects across sets: the drawings and the marker records."""

    drawn: dict[Id[Page], Drawing]
    markers: list[LinkMarker]


@dataclass(frozen=True)
class _Run:
    """What every drawing set of one `lay_out` call shares; `sink` is `lay_out_drawn`'s."""

    model: Model
    problem: PlacementProblem
    kit: SymbolKit
    chosen: Options
    conventions: Conventions
    library: Library
    sink: _Sink | None = None


def _one_set(
    run: _Run,
    laid: Model,
    part: PlacementProblem,
    scope: DrawingScope,
    number: int,
) -> tuple[Model, tuple[Finding, ...]]:
    """`part` (`scope`'s share of the problem) solved and written into `laid`; its findings.

    With a `sink` the set's drawings and markers are added to it (`write_layout_drawn`).
    """
    pins = [PinRef(s.id, p.id) for s in part.symbols for p in s.pins]
    fit = marker_fit(run.model, run.kit, scope.of_unit, run.library, pins)
    wide = link_fit(run.model, run.kit, run.library, scope.of_unit)
    turned, above, below = facing_views()
    layout = solve(
        part,
        replace(
            run.chosen,
            marker_fit=fit,
            link_fit=wide,
            marker_vertical=turned,
            marker_above=above,
            marker_below=below,
        ),
    )
    given = {
        "library": run.library,
        "where": SetPlace(location=scope.location, number=number),
    }
    sink = run.sink
    if sink is None:
        laid, more = write_layout(laid, scope.of_unit, layout, part, run.kit, **given)
    else:
        laid, more, drawn, markers = write_layout_drawn(
            laid, scope.of_unit, layout, part, run.kit, **given
        )
        sink.drawn.update(drawn)
        sink.markers.extend(markers)
    return laid, (
        *cut_net_findings(run.model, run.problem, scope, number),
        *set_without_page_findings(run.problem, scope, layout, number),
        *more,
    )


def _lay_out(  # noqa: PLR0913 - lay_out's five and the sink, by keyword
    model: Model,
    kit: SymbolKit,
    problem: PlacementProblem,
    conventions: Conventions,
    library: Library,
    *,
    sink: _Sink | None,
) -> tuple[Model, tuple[Finding, ...]]:
    scopes = drawing_scopes(model, kit)
    if problem.symbols and not scopes:
        refuse("the kit", "has no function for the problem's symbols: pass the build's kit")
    run = _Run(model, problem, kit, options(conventions, library), conventions, library, sink)
    laid = model
    found: list[Finding] = []
    for number, scope in enumerate(scopes, 1):
        part = restrict(problem, scope)
        try:
            laid, more = _one_set(run, laid, part, scope, number)
        except _SET_FAILURES as error:
            found.append(set_failure_finding(error, part, scope, number))
        else:
            found.extend(more)
    return laid, tuple(found)


def lay_out(
    model: Model,
    kit: SymbolKit,
    problem: PlacementProblem,
    conventions: Conventions,
    library: Library,
) -> tuple[Model, tuple[Finding, ...]]:
    """`problem` solved once per drawing set of the kit's functions and written into `model`.

    The sets are `drawing_scopes`' order: the top level by location, then each unit; set `n` is `n`.
    A set whose layout raises gives one ERROR naming it and draws no page; the other sets lay out.
    """
    return _lay_out(model, kit, problem, conventions, library, sink=None)


def lay_out_drawn(
    model: Model,
    kit: SymbolKit,
    problem: PlacementProblem,
    conventions: Conventions,
    library: Library,
) -> tuple[
    Model,
    tuple[Finding, ...],
    Mapping[Id[Page], Drawing],
    Mapping[Id[Page], tuple[ReferenceLink, ...]],
]:
    """`lay_out`'s model and findings, then the page `Drawing`s and each page's reference links.

    The drawings come straight from the layouts (F7); the links equal
    `derive.page_nav.reference_links` over the pages of the drawings.
    """
    sink = _Sink({}, [])
    laid, found = _lay_out(model, kit, problem, conventions, library, sink=sink)
    drawings, links = finish_drawings(laid, sink.drawn, sink.markers, ORIGIN, library)
    net = drawn_netlist(laid, kit, drawings, sink.markers, library)
    return (
        laid,
        (*found, *drawing_sweep(laid, net, found)),
        drawings,
        links,
    )
