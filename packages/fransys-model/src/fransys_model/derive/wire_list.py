"""The wire list: one row per wire no harness carries, by its printed ends.

See design/derive-queries.md; a query leaves out what it cannot render (decision 0021).
"""

from fransys_model.derive.facts.harness_wires import wire_harnesses
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import conductors, facets_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Unit

from .designation import unit_list_context
from .drawing_text import wire_text
from .order import natural_key
from .report_scope import _conductor_belongs, _require_unit
from .rows import WireRow
from .texts.context import PrintContext
from .texts.end_text import FAR_END, end_text
from .wire_ends import ordered_wire_ends


def _wire_row(
    model: Model,
    conductor: Conductor,
    facet: WireFacet,
    context: Id[AspectNode] | None,
    unit: Id[Unit] | None,
) -> WireRow:
    end_from, end_to = ordered_wire_ends(model, conductor.a, conductor.b)
    ctx = PrintContext(reading=unit, location=context)
    return WireRow(
        conductor=conductor.id,
        from_=end_text(model, end_from, FAR_END, ctx),
        to=end_text(model, end_to, FAR_END, ctx),
        colour=facet.colour,
        cross_section_mm2=facet.gauge_mm2,
        label=wire_text(model, conductor.id, unit=unit),
    )


def wire_rows(
    model: Model, *, unit: Id[Unit] | None = None, context: Id[AspectNode] | None = None
) -> tuple[WireRow, ...]:
    """One `WireRow` per `wire`-faceted `WIRE` conductor no harness carries, by `(from, to, id)`.

    A jumper, a cable core, a link and a harness wire never get a row. `from`/`to` are
    the ends as the list prints them (`unit` and `context` act the same); `label` is `wire_text`.
    """
    return tuple(
        row
        for row in _all_wire_rows(model, unit, context)
        if not wire_harnesses(model, row.conductor)
    )


def _all_wire_rows(
    model: Model, unit: Id[Unit] | None, context: Id[AspectNode] | None
) -> tuple[WireRow, ...]:
    """Every `WireRow`, harness wires too: the one builder `wire_rows` and `harness_wires` share."""
    _require_unit(model, unit)
    context = unit_list_context(model, unit, context)
    wire_of = {facet.subject: facet for facet in facets_of(model, WireFacet).values()}
    rows = [
        _wire_row(model, conductor, wire_of[conductor.id], context, unit)
        for conductor in conductors(model).values()
        if conductor.id in wire_of
        and conductor.kind is ConductorKind.WIRE
        and (unit is None or _conductor_belongs(model, conductor, unit))
    ]
    return tuple(
        sorted(rows, key=lambda row: (natural_key(row.from_), natural_key(row.to), row.conductor))
    )
