"""Stage 2, columns: the series chains that are placed top to bottom (design/columns.md 6.2)."""

import itertools
from typing import TYPE_CHECKING, TypeGuard

from fransys_layout.geometry import HintError, LayoutError
from fransys_model.kernel import Finding, Severity

from .types import ROLE_ORDER, Cell, Column, Role

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import (
        Chain,
        ChainEntry,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
    )

FUNCTION_UNPLACED_IN_COLUMN = "FUNCTION_UNPLACED_IN_COLUMN"

_TERMINAL_PORTS = 2  # a strip terminal has an inner and an outer port


def replica_key(served: AuthoringKey, terminal: AuthoringKey) -> AuthoringKey:
    """The key of the replica column showing `terminal`, right after `served` (columns.md 6.2)."""
    return (*served, "terminal", *terminal)  # vocab-ok: a key component, not a kind test


def boundary_key(function_key: AuthoringKey, parent_unit_key: AuthoringKey | None) -> AuthoringKey:
    """The key of a unit boundary function's black-box replica, keyed by its parent (U1)."""
    parent = parent_unit_key if parent_unit_key is not None else ("top",)
    return (*function_key, "boundary", *parent)


def is_rack_key(key: AuthoringKey | None) -> TypeGuard[AuthoringKey]:
    """F1: whether a column key stands in a rack, `("rack", <rack>, <position>, ...)`."""
    return key is not None and len(key) > 0 and key[0] == "rack"


def columns_from_chains(
    chains: tuple[Chain, ...],
    functions: tuple[FunctionSpec, ...],
    *,
    drawn: tuple[DrawnFunction, ...] = (),
    connections: tuple[Connection, ...] = (),
) -> tuple[tuple[Column, ...], tuple[Finding, ...]]:
    """Turn every chain into one column and every other function into its own (WP5, columns 6.2)."""
    specs = {spec.function: spec for spec in functions}
    drawn_by = {one.function: one for one in drawn}
    claimed: set[Handle] = set()
    columns = []
    for chain in sorted(chains, key=lambda chain: (chain.key, chain.chain)):
        if not chain.entries:
            msg = "a chain has no entries"
            raise HintError(msg, subjects=(chain.chain,))
        steps = []
        for entry in chain.entries:
            spec = specs.get(entry.function)
            if spec is None:
                msg = "a chain names a function that is not drawn"
                raise HintError(msg, subjects=(chain.chain, entry.function))
            if spec.function in claimed:
                msg = "a function is in two chains, or twice in one chain"
                raise HintError(msg, subjects=(chain.chain, spec.function))
            claimed.add(spec.function)
            steps.append((entry, spec))
        _check_series(chain, steps)
        flipped = _entered_from_south(steps, drawn_by, connections)
        cells = tuple(
            Cell(function=entry.function, index=entry.index, flip=entry.function in flipped)
            for entry in chain.entries
        )
        columns.append(build_column(chain.key, cells, [spec for _, spec in steps]))
    findings = []
    for spec in sorted(specs.values(), key=lambda spec: spec.function):
        if spec.function in claimed:
            continue
        columns.append(build_column(spec.key, (Cell(function=spec.function, index=0),), [spec]))
        findings.append(
            Finding(
                code=FUNCTION_UNPLACED_IN_COLUMN,
                severity=Severity.INFO,
                subjects=(spec.function,),
                message="function is in no chain: placed alone in a column of its own",
            )
        )
    columns.sort(key=lambda column: (column.key, tuple(cell.function for cell in column.cells)))
    return tuple(columns), tuple(findings)


def _check_series(chain: Chain, steps: Sequence[tuple[ChainEntry, FunctionSpec]]) -> None:
    """Raise unless consecutive entries have distinct indices and share a physical net."""
    for (above, upper), (below, lower) in itertools.pairwise(steps):
        if above.index == below.index:
            msg = "two entries of a chain share an index"
            subjects = tuple(sorted((upper.function, lower.function)))
            raise HintError(msg, subjects=(chain.chain, *subjects))
        upper_nets = {port.physical_net for port in upper.ports}
        if not any(port.physical_net in upper_nets for port in lower.ports):
            msg = "consecutive functions of a chain are not joined"
            raise HintError(msg, subjects=(chain.chain, upper.function, lower.function))


def _entered_from_south(
    steps: Sequence[tuple[ChainEntry, FunctionSpec]],
    drawn_of: Mapping[Handle, DrawnFunction],
    connections: tuple[Connection, ...],
) -> set[Handle]:
    """The terminals of a chain entered by their S-facing port (D1); an ambiguous one stays."""
    joined = {(c.a.port, c.b.port) for c in connections} | {
        (c.b.port, c.a.port) for c in connections
    }
    flipped: set[Handle] = set()
    for at, (_, spec) in enumerate(steps):
        drawing = drawn_of.get(spec.function)
        if not spec.roles.terminal or len(spec.ports) != _TERMINAL_PORTS:
            continue
        if drawing is None:
            if drawn_of:
                msg = "a terminal of a chain has no drawn function to read its facing from"
                raise LayoutError(msg)
            continue
        if at > 0:
            neighbour = {port.port for port in steps[at - 1][1].ports}
            entries = [p for p in spec.ports if any((p.port, n) in joined for n in neighbour)]
        elif len(steps) > 1:
            neighbour = {port.port for port in steps[1][1].ports}
            entries = [p for p in spec.ports if all((p.port, n) not in joined for n in neighbour)]
        else:
            continue
        if len(entries) != 1:
            continue
        (entry,) = entries
        (other,) = (port for port in spec.ports if port is not entry)
        symbol_port = {dp.port: dp.symbol_port for dp in drawing.ports}
        if entry.port not in symbol_port or other.port not in symbol_port:
            msg = "a terminal port of a chain does not map to a symbol port"
            raise LayoutError(msg)
        facing = {g.name: g.facing.value for g in drawing.geometry.ports}
        if (
            facing.get(symbol_port[entry.port]) == "s"
            and facing.get(symbol_port[other.port]) == "n"
        ):
            flipped.add(spec.function)
    return flipped


def build_column(
    key: AuthoringKey,
    cells: tuple[Cell, ...],
    members: Sequence[FunctionSpec],
) -> Column:
    """One column over `members`: group hint, else deepest shared `=` node; one unit, else error."""
    hinted = [spec for spec in members if spec.group_hint is not None]
    clash = next((spec for spec in hinted if spec.group_hint != hinted[0].group_hint), None)
    if clash is not None:
        msg = "two cells of one column carry different group hints"
        raise HintError(msg, subjects=tuple(sorted((hinted[0].function, clash.function))))
    # C21 (deep dive): a column's group is its devices' group; a terminal at its end is a
    # boundary of another group (X01 of =SUP heading =P1's chain), not a member
    # (nor a PLC channel end: F12 97/98 -> DI1 is P1's feedback column, designer ruling)
    devices = [
        spec for spec in members if spec.roles.sets_group and spec.pin_function is None
    ] or members
    # layout-0103: a column holding an item box takes the box's group, whatever stands under it
    devices = [s for s in devices if s.function.kind == "item"] or devices
    # layout-0103: an external member (no group of its own, +EXT by others) does not count
    devices = [s for s in devices if s.group_path] or devices
    groups = _common_prefix([spec.group_path for spec in devices])
    locations = _common_prefix([spec.location_path for spec in members])
    units = {spec.unit for spec in members}
    if len(units) > 1:
        msg = "two cells of one column belong to different units"
        raise LayoutError(msg)
    roles = (port.role for spec in members for port in spec.ports)
    return Column(
        key=key,
        cells=cells,
        group=hinted[0].group_hint if hinted else (groups[-1] if groups else None),
        role=min(roles, key=ROLE_ORDER.index, default=Role.CONTROL),
        location=locations[-1] if locations else None,
        unit=next(iter(units)),
    )


def _common_prefix(paths: Sequence[tuple[Handle, ...]]) -> tuple[Handle, ...]:
    """The longest run of nodes, from the root, that every path starts with."""
    prefix = []
    for nodes in zip(*paths, strict=False):
        if any(node != nodes[0] for node in nodes):
            break
        prefix.append(nodes[0])
    return tuple(prefix)
