"""`lay_out_drawn`: the core path, one drawing set per (unit, location) (PAGE-02, Rulings 50 and 70)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CoreError, PinRef, solve
from fransys_model.derive import refuses
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from .draw_layout import finish_drawings
from .draw_write import ORIGIN, write_layout_drawn
from .drawn_netlist import drawn_netlist, with_lines
from .drawn_sweep import drawing_sweep
from .drawn_where import where_joined
from .placement_kit import ProblemError, refuse
from .placement_markers import facing_views, stub_fit
from .placement_options import options, sheet_area
from .placement_sets import bare_pins, cut_lines, drawing_scopes, restriction, scope_groups
from .placement_widest import link_fit
from .set_findings import set_failure_finding, set_without_page_findings
from .write_pages import SetPlace
from .write_tables import place_texts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import Options, PlacementProblem
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import LinkMarker, Page

    from .placement_kit import SymbolKit
    from .placement_options import Conventions
    from .placement_sets import DrawingScope, Restriction

__all__ = ["lay_out_drawn"]

# KeyError and IndexError are core faults that today escape `solve`; one set's fault must not
# hide the sets that lay out (FLIP-NOW F2, KI-022), so they are findings until the core names them.
_SET_FAILURES = (CoreError, ProblemError)


@dataclass(frozen=True)
class _Sink:
    """What `lay_out_drawn` collects across sets: the drawings and the marker records."""

    drawn: dict[Id[Page], Drawing]
    markers: list[LinkMarker]
    pageless: list[tuple[DrawingScope, int]]

    def take(
        self,
        drawn: Mapping[Id[Page], Drawing],
        markers: Sequence[LinkMarker],
        pageless: tuple[DrawingScope, int] | None,
    ) -> None:
        """Add a set's drawings, markers and, if it got no page, its number."""
        if pageless is not None:
            self.pageless.append(pageless)
        self.drawn.update(drawn)
        self.markers.extend(markers)


@dataclass(frozen=True)
class _Run:
    """What every drawing set of one `lay_out_drawn` call shares."""

    model: Model
    problem: PlacementProblem
    kit: SymbolKit
    chosen: Options
    conventions: Conventions
    library: Library
    sink: _Sink


def _one_set(
    run: _Run,
    laid: Model,
    cuts: Restriction,
    scope: DrawingScope,
    number: int,
) -> tuple[Model, tuple[Finding, ...]]:
    """`part` (`scope`'s share of the problem) solved and written into `laid`; its findings.

    The set's drawings and markers are added to the run's sink (`write_layout_drawn`).
    """
    part = replace(cuts.problem, area=sheet_area(sheet_for(run.model, PageKind.SCHEMATIC)))
    pins = [PinRef(s.id, p.id) for s in part.symbols for p in s.pins]
    fit, lines, table = stub_fit(run.model, run.kit, (scope.of_unit, run.library), pins)
    wide = link_fit(run.model, run.kit, run.library, scope.of_unit)
    turned, above, below = facing_views()
    base = replace(run.chosen, link_fit=wide, marker_vertical=turned, marker_above=above, marker_below=below)
    layout = solve(part, replace(base, marker_fit=fit, stub_lines=lines, stub_table=table))
    layout = replace(layout, pages=scope_groups(layout.pages, part, scope))
    laid, more, drawn, markers = write_layout_drawn(
        laid,
        scope.of_unit,
        layout,
        part,
        run.kit,
        library=run.library,
        where=SetPlace(location=scope.location, number=number),
    )
    run.sink.take(drawn, markers, (scope, number) if scope.symbols and not layout.pages else None)
    return laid, more


def _lay_out(run: _Run) -> tuple[Model, tuple[Finding, ...], Mapping[PinRef, str]]:
    model, kit, problem = run.model, run.kit, run.problem
    scopes = drawing_scopes(model, kit)
    if problem.symbols and not scopes:
        refuse("the kit", "has no function for the problem's symbols: pass the build's kit")
    bare, lines = bare_pins(model, kit), cut_lines(model, kit)
    laid = model
    found: list[Finding] = []
    for number, scope in enumerate(scopes, 1):
        cuts = restriction(problem, scope, bare, lines, scopes)
        try:
            laid, more = _one_set(run, laid, cuts, scope, number)
        except _SET_FAILURES as error:
            found.append(set_failure_finding(error, cuts.problem, scope, number))
        else:
            found.extend(more)
    return laid, tuple(found), lines


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
]:
    """The laid model and its findings, then the page `Drawing`s.

    The drawings come straight from the layouts (F7).
    """
    sink = _Sink({}, [], [])
    run = _Run(model, problem, kit, options(conventions, library), conventions, library, sink)
    laid, found, lines = _lay_out(run)
    if refuses(found):
        undrawn: dict[Id[Page], Drawing] = {}
        return laid, found, undrawn  # the layout stopped on an ERROR: nothing is drawn, so no drawing check runs (KI-773)
    drawings = finish_drawings(laid, sink.drawn, sink.markers, ORIGIN, library)
    drawings = place_texts(laid, kit, library, drawings)
    net = with_lines(drawn_netlist(laid, kit, drawings, sink.markers, library), laid, kit, lines)
    net.texted.update(where_joined(laid, net))
    return (
        laid,
        (
            *found,
            *set_without_page_findings(laid, kit, net, sink.pageless),
            *drawing_sweep(laid, net),
        ),
        drawings,
    )
