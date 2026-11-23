"""`lay_out_drawn`: the core path, one drawing set per (unit, location) (PAGE-02, Rulings 50 and 70)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core import CoreError, PinRef, solve

from .draw_layout import alone_of, finish_drawings
from .draw_outlines import outline_titles
from .draw_write import ORIGIN, write_layout_drawn
from .drawn_ids import core_symbol_id
from .drawn_netlist import drawn_netlist, with_lines
from .drawn_sweep import drawing_sweep
from .drawn_where import where_joined, where_named
from .placement_env import make_env
from .placement_joins import node_joins
from .placement_kit import ProblemError, refuse
from .placement_markers import facing_views, marker_boxes_value
from .placement_options import options
from .placement_syms import strip_tags
from .restrict import restriction
from .scopes import bare_pins, cut_lines, drawing_scopes, frame_titles, piece_names
from .set_findings import read_incomplete_finding, set_failure_finding, set_without_page_findings, skipped_ports
from .write_pages import SetPlace
from .write_tables import place_texts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout, Options, PlacementProblem
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import LinkMarker, Page

    from .placement_kit import SymbolKit
    from .placement_options import Conventions
    from .restrict import Restriction
    from .scopes import DrawingScope

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
    failed: list[DrawingScope]  # sets whose layout raised or write skipped its output steps: not checked (KI-779, R1991)
    alone: set[tuple[Id[Page], str]]  # (page, drawn symbol) alone in its run there: PRINTED_TEXT_WRONG reads the tags back against them
    titles: dict[str, str]  # the title each drawn frame owes
    refused_pages: set[Id[Page]]  # the pages of the skipped sets: returned, never read by a drawn-page check (R1996)

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


def _keep_read_back(run: _Run, layout: CoreLayout, drawn: Mapping[Id[Page], Drawing]) -> None:
    """The facts `PRINTED_TEXT_WRONG` reads a set's drawings back against, kept on the sink."""
    alone = {core_symbol_id(s) for s in alone_of(layout)}
    run.sink.alone.update((page, s.id) for page, d in drawn.items() for s in d.symbols if s.id in alone)
    run.sink.titles.update(outline_titles(layout, frame_titles(run.model, run.kit)))


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
    part = cuts.problem
    pins = [PinRef(s.id, p.id) for s in part.symbols for p in s.pins]
    boxes, lines, table = marker_boxes_value(run.model, run.kit, (scope.of_unit, run.library), pins)
    turned, above, below = facing_views()
    base = replace(run.chosen, untitled=scope.copies, marker_vertical=turned, marker_above=above, marker_below=below)
    layout = solve(part, replace(base, marker_boxes=boxes, stub_lines=lines, stub_table=table))
    laid, more, drawn, markers, skipped = write_layout_drawn(
        laid,
        scope.of_unit,
        layout,
        part,
        run.kit,
        library=run.library,
        where=SetPlace(location=scope.location, number=number),
    )
    _keep_read_back(run, layout, drawn)
    run.sink.take(drawn, markers, (scope, number) if scope.symbols and not layout.pages else None)
    if skipped:
        run.sink.failed.append(scope)  # write skipped its output steps: the drawing is incomplete (KI-773, R1991)
        run.sink.refused_pages.update(drawn)
    return laid, more


def _lay_out(run: _Run) -> tuple[Model, tuple[Finding, ...], Mapping[PinRef, str]]:
    model, kit, problem = run.model, run.kit, run.problem
    scopes = drawing_scopes(model, kit)
    if problem.symbols and not scopes:
        refuse("the kit", "has no function for the problem's symbols: pass the build's kit")
    bare, lines, tags = bare_pins(model, kit), cut_lines(model, kit), strip_tags(make_env(model, kit, run.conventions, run.library))
    joins = node_joins(kit, run.library)
    found: list[Finding] = []  # model becomes the laid model set by set
    for number, scope in enumerate(scopes, 1):
        cuts = restriction(
            problem, scope, bare, lines, scopes, options=run.conventions.options, tags=tags, pieces=piece_names(run.model, kit, scope, joins)
        )
        try:
            model, more = _one_set(run, model, cuts, scope, number)
        except _SET_FAILURES as error:
            more = (set_failure_finding(error, cuts.problem, scope, number),)  # a PLACEMENT_PROBLEM ERROR
            run.sink.failed.append(scope)  # a raised layout; a set whose drawing is complete is checked, whatever its findings (R1987, R1991)
        found.extend(more)
    return model, tuple(found), lines


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
    sink = _Sink({}, [], [], [], set(), {}, set())
    run = _Run(model, problem, kit, options(conventions, library), conventions, library, sink)
    laid, found, lines = _lay_out(run)
    drawings = finish_drawings(laid, sink.drawn, sink.markers, ORIGIN, library)
    drawings = place_texts(laid, kit, library, drawings)
    checked = {k: v for k, v in drawings.items() if k not in sink.refused_pages}
    net = with_lines(drawn_netlist(laid, kit, checked, sink.markers, library), laid, kit, lines)
    net.texted.update(where_joined(laid, net))
    net.named.update(where_named(laid, net))
    net.alone.update(sink.alone)
    net.titles.update(sink.titles)
    net.skipped.update(skipped_ports(laid, kit, sink.failed))
    unread = (
        (read_incomplete_finding(tuple(k for k in drawings if k in sink.refused_pages), net.skipped),) if sink.failed or sink.refused_pages else ()
    )
    return (
        laid,
        (
            *found,
            *set_without_page_findings(laid, kit, net, sink.pageless),
            *drawing_sweep(laid, net),
            *unread,
        ),
        drawings,
    )
