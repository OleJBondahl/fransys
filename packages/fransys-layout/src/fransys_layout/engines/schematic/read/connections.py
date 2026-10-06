"""Reads of the model for the connection filters of `read_inputs` (decision layout-0044, spec B2).

A connection, net group or rail whose ends all sit on one opaque board is dropped silently; one
with an undrawn end is dropped and reported `CONNECTION_TO_UNDRAWN`.
"""

import dataclasses
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.schematic.read.views import is_board_internal, item_of
from fransys_layout.lint.codes import CONNECTION_TO_UNDRAWN
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import ports as ports_table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages import Connection, NetGroup, PortRef, Rail
    from fransys_model.kernel import Id, Model


def _undrawn_finding(refs: Iterable[PortRef], *, noun: str) -> Finding:
    subjects = tuple(sorted(ref.port for ref in refs))
    return Finding(
        code=CONNECTION_TO_UNDRAWN,
        severity=Severity.WARNING,
        subjects=subjects,
        message=f"a {noun} has an end that is not drawn",
    )


def split_connections(
    model: Model, connections: tuple[Connection, ...], drawn: AbstractSet[Id[Any]]
) -> tuple[tuple[Connection, ...], tuple[Finding, ...], frozenset[Id[Any]]]:
    """Split off the connections with an undrawn end (or board-internal); report the former."""
    kept: list[Connection] = []
    findings: list[Finding] = []
    stranded: set[Id[Any]] = set()
    for connection in connections:
        if is_board_internal(model, (item_of(model, connection.a), item_of(model, connection.b))):
            continue
        undrawn = [ref for ref in (connection.a, connection.b) if ref.function not in drawn]
        if not undrawn:
            kept.append(connection)
            continue
        findings.append(_undrawn_finding(undrawn, noun="connection"))
        stranded |= {ref.port for ref in (connection.a, connection.b) if ref.function in drawn}
    return tuple(kept), tuple(findings), frozenset(stranded)


def split_net_groups(
    model: Model, net_groups: tuple[NetGroup, ...], drawn: AbstractSet[Id[Any]]
) -> tuple[tuple[NetGroup, ...], tuple[Finding, ...], frozenset[Id[Any]]]:
    """Split off the net groups with an undrawn end (or board-internal); report the former."""
    kept: list[NetGroup] = []
    findings: list[Finding] = []
    stranded: set[Id[Any]] = set()
    for group in net_groups:
        if is_board_internal(model, (item_of(model, ref) for ref in group.ports)):
            continue
        undrawn = [ref for ref in group.ports if ref.function not in drawn]
        if not undrawn:
            kept.append(group)
            continue
        findings.append(_undrawn_finding(undrawn, noun="net group"))
        stranded |= {ref.port for ref in group.ports if ref.function in drawn}
    return tuple(kept), tuple(findings), frozenset(stranded)


def split_rails(
    model: Model, rails: tuple[Rail, ...], drawn: AbstractSet[Id[Any]]
) -> tuple[Rail, ...]:
    """Drop a board-internal rail; otherwise keep only its drawn ports."""
    kept = []
    for rail in rails:
        item_ids = [functions_table(model)[_port_function(model, port)].item for port in rail.ports]
        if is_board_internal(model, item_ids):
            continue
        drawn_ports = tuple(port for port in rail.ports if _port_function(model, port) in drawn)
        if drawn_ports:
            kept.append(dataclasses.replace(rail, ports=drawn_ports))
    return tuple(kept)


def _port_function(model: Model, port: Id[Any]) -> Id[Any]:
    return ports_table(model)[port].function
