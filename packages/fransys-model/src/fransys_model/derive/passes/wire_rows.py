"""The wire-row pass: a hinted wire gets its `WireFacet` from what its nets carry (model-0260).

A `WireRowHint` is a wire the author could not give a row. Its row is, in order, the `source_row` a
port of its physical net states, the DC signal row when a PLC channel of a DC signal sits on the
net, else the one row the rails its ends carry give. A rail counts only inside the wire's own
unit and the units below it. Nothing resolved is a `WIRE_ROW_UNRESOLVED` `ERROR`.
"""

import dataclasses
from typing import TYPE_CHECKING, Final

from fransys_model.derive.lookups import item_of_port, unit_chain
from fransys_model.kernel import Finding, Model, Severity, evolve, make_id
from fransys_model.vocab.closure import net_of, port_rails
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.facets.wire_row_hint import WireRowHint
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.supply_system import supply_rail_row
from fransys_model.vocab.tables import (
    conductors,
    facets_of,
    functions,
    items,
    nets,
    ports,
    supply_systems,
)
from fransys_model.vocab.wiring_rows import WiringRow

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Port, Unit

WIRE_ROW_UNRESOLVED: Final[str] = "WIRE_ROW_UNRESOLVED"
_DC_SIGNALS: Final = frozenset(SignalType) - {SignalType.RELAY}  # a relay output may switch AC


def _on_net(model: Model, conductor: Conductor) -> tuple[Id[Port], ...]:
    net = net_of(model, conductor.a)
    return net.ports if net is not None else (conductor.a, conductor.b)


def _sourced(model: Model, net_ports: tuple[Id[Port], ...]) -> set[WiringRow]:
    stated = {ports(model)[p].source_row for p in net_ports}
    return {row for row in stated if row is not None}


def _signal_on(model: Model, net_ports: tuple[Id[Port], ...]) -> bool:
    channels = {f.subject: f.signal for f in facets_of(model, PlcChannelFacet).values()}
    fns, table = functions(model), ports(model)
    return any(
        channels.get(fns[table[p].function].template) in _DC_SIGNALS
        for p in net_ports
        if fns[table[p].function].template is not None
    )


def _in_scope(model: Model, wire_unit: Id[Unit] | None, supply_unit: Id[Unit] | None) -> bool:
    """Whether a supply declared in `supply_unit` reaches a wire of `wire_unit` (unit limit)."""
    if wire_unit is None:
        return True
    return supply_unit is not None and wire_unit in unit_chain(model, supply_unit)


def _rail_rows(model: Model, conductor: Conductor) -> set[WiringRow]:
    unit = items(model)[item_of_port(model, conductor.a)].unit
    carried = port_rails(model, conductor.a) | port_rails(model, conductor.b)
    rows: set[WiringRow] = set()
    for supply in supply_systems(model).values():
        if _in_scope(model, unit, supply.unit):
            rows.update(
                row
                for rail in carried & set(supply.rails)
                if (row := supply_rail_row(supply, rail)) is not None
            )
    return rows


def _row(model: Model, conductor: Conductor) -> tuple[WiringRow | None, str]:
    """The row of `conductor`, or `None` and why there is none."""
    net_ports = _on_net(model, conductor)
    stated = _sourced(model, net_ports)
    if len(stated) > 1:
        return None, f"its net's pins state rows {', '.join(sorted(stated))}"
    if stated:
        return next(iter(stated)), ""
    if _signal_on(model, net_ports):
        return WiringRow.DC_SIGNAL, ""
    rows = _rail_rows(model, conductor)
    if len(rows) > 1:
        return None, f"its ends carry rails of rows {', '.join(sorted(rows))}"
    if rows:
        return next(iter(rows)), ""
    return None, "its net carries no rail of its unit and no pin states a row"


def _net_name(model: Model, conductor: Conductor) -> str:
    here = set(_on_net(model, conductor))
    named = sorted(n.name for n in nets(model).values() if n.name and here & set(n.ports))
    return f"net {named[0]!r}" if named else "an unnamed net"


def _unresolved(model: Model, hint: WireRowHint, conductor: Conductor, why: str) -> Finding:
    message = (
        f"the wire from {ref(conductor.a)} to {ref(conductor.b)} on {_net_name(model, conductor)} "
        f"has no row: {why}. Give wire= on that series (a size and a colour, or a row table)"
    )
    return Finding(
        code=WIRE_ROW_UNRESOLVED,
        severity=Severity.ERROR,
        subjects=(hint.id, conductor.id),
        message=message,
    )


def _facet(hint: WireRowHint, conductor: Conductor, row: WiringRow) -> WireFacet | str:
    """The facet the hint's table gives `row`, or why it cannot."""
    spec = hint.rows.get(row.value)
    if spec is None:
        return f"its table has no row {row.value}"
    gauge = hint.gauge_mm2 if hint.gauge_mm2 is not None else spec.gauge_mm2
    if gauge is None:
        return f"row {row.value} has no size"
    key = (*conductor.key, "facet")
    return WireFacet(
        id=make_id(WireFacet, key),
        key=key,
        subject=conductor.id,
        colour=spec.colour,
        gauge_mm2=gauge,
        length_mm=None,
        label=hint.label,
    )


def _resolved(model: Model, hint: WireRowHint) -> WireFacet | Finding:
    """The facet of one hinted wire, or the finding that says why it has none."""
    conductor = conductors(model)[hint.subject]
    row, why = _row(model, conductor)
    facet = _facet(hint, conductor, row) if row is not None else why
    return _unresolved(model, hint, conductor, facet) if isinstance(facet, str) else facet


def resolve_wire_rows(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Write the `WireFacet` of every hinted wire from its row; the rest are `ERROR` findings.

    A wire that already has a facet is skipped, so a second run changes nothing and the model
    comes back as the same object when nothing is hinted.
    """
    done = {f.subject for f in facets_of(model, WireFacet).values()}
    hints = sorted(
        (h for h in facets_of(model, WireRowHint).values() if h.subject not in done),
        key=lambda h: h.id,
    )
    results = [(hint, _resolved(model, hint)) for hint in hints]
    findings = tuple(r for _, r in results if isinstance(r, Finding))
    made = [(r, hint) for hint, r in results if isinstance(r, WireFacet)]
    if not made:
        return model, findings
    origins = {facet.id: model.origins[hint.id] for facet, hint in made}
    evolved = evolve(model, put=[f for f, _ in made], origin=next(iter(origins.values())))
    return dataclasses.replace(
        evolved, origins=frozendict({**evolved.origins, **origins})
    ), findings
