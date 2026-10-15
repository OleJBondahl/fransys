"""Stage 2's steps, one function each: the columns of the run, from discovery to replicas."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages import Column, DrawnFunction, column_widths, columns_from_chains
from fransys_layout.stages.arrange import (
    cut_locations,
    edge_mates,
    inline_exits,
    join_strip_rows,
    rack_order,
    same_unit_connectivity,
)
from fransys_layout.stages.attach import attach_replicas, hub_order
from fransys_layout.stages.boxes import port_ranks, power_maps, turning_ports
from fransys_layout.stages.chains import ChainRecords, discover_chains
from fransys_layout.stages.device_columns import device_columns
from fransys_layout.stages.far_ends import (
    FarInputs,
    group_map,
    is_channel,
    move_far_ends,
    sheet_fits,
)
from fransys_layout.stages.pin_ends import pin_keyed
from fransys_layout.stages.pin_landing import Power, function_landing, lanes_in_pin_order
from fransys_layout.stages.references.nets import star_wires
from fransys_layout.stages.replicate import replicate_boundaries, replicate_terminals
from fransys_layout.stages.terminal_rows import join_terminal_rows, terminal_chains
from fransys_layout.stages.types import Home
from fransys_layout.stages.wire_copies import with_wire_copies
from fransys_layout.stages.wired_copies import (
    emptied_groups,
    loose_groups,
    without_groups,
    without_unwired_copies,
)

from ._stub_seats import far_set_seats, stub_seats
from .defaults import HEADROOM_LANES
from .read.column_places import in_key_order
from .read.harness_lines import line_reads
from .read.reading import key_orders, terminal_sort_keys
from .read.units import boundary_parents, unit_boundaries

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import Handle
    from fransys_model.kernel import Finding, Model

    from .read import StageInputs


def discovered_columns(
    model: Model,
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    rank_of: Mapping[Any, int],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> tuple[Column, ...]:
    """The columns discovery finds over every function no chain claims, cut at locations."""
    # Discovery runs first, over every function no chain claims, so a hinted chain always wins
    # A chain never gets a function discovery already placed, nor a device chain's member
    chain_claimed = {m for chain in inputs.device_chains for m in chain.members} | {
        entry.function for chain in inputs.chains for entry in chain.entries if not entry.box
    }
    undiscovered = tuple(spec for spec in inputs.functions if spec.function not in chain_claimed)
    # Chains are discovered from connectivity alone.
    # A chain never spans two units: discovery sees same-unit connectivity only.
    same = same_unit_connectivity(
        inputs.functions, inputs.connections, inputs.net_groups, inputs.mates
    )
    records = ChainRecords(
        undiscovered,
        drawn,
        *same,
        edge_mates=edge_mates(boundary_parents(model), inputs.functions, inputs.mates),
        fixed=frozenset(inputs.item_north + inputs.item_south),
    )
    discovered = discover_chains(
        pin_keyed(records), rank_of=rank_of, tie_key=tie_key, key_order=key_orders(inputs.functions)
    )
    # A column never spans locations; the conductors between two are stubs
    return cut_locations(discovered, inputs.functions)


def chained_columns(
    inputs: StageInputs, drawn: tuple[DrawnFunction, ...], discovered: tuple[Column, ...]
) -> tuple[tuple[Column, ...], tuple[Finding, ...]]:
    """The hinted chains' columns, over the functions discovery left, and their findings."""
    # An edge pin's face replica is not its home; its home column still comes below; a device
    # chain's column is among `discovered`
    placed_by_discovery = {
        cell.function
        for column in discovered
        for cell in column.cells
        if cell.home is not Home.ELSEWHERE
    }
    return columns_from_chains(
        inputs.chains,
        tuple(spec for spec in inputs.functions if spec.function not in placed_by_discovery),
        drawn=drawn,
        connections=inputs.connections,
        boxes={spec.function: spec for spec in inputs.functions if spec.roles.item_view},
    )


def ordered_columns(
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> tuple[tuple[Column, ...], Any]:
    """The columns with join strip and terminal rows, rack-ordered, and the terminal chains."""
    all_columns = join_strip_rows(columns, inputs.functions)
    chains = terminal_chains(inputs.functions, drawn, inputs.connections)
    all_columns = join_terminal_rows(
        all_columns,
        inputs.functions,
        chains,
        tie_key=tie_key,
        fits=lambda row: (
            column_widths((row,), drawn, profile=inputs.profile)[0].width
            <= inputs.sheet.inner_width
        ),
    )
    return rack_order(all_columns, inputs.functions), chains


def replicated_columns(
    model: Model,
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    all_columns: tuple[Column, ...],
) -> tuple[StageInputs, tuple[DrawnFunction, ...], tuple[Column, ...]]:
    """The columns with terminal, boundary and attached replicas, far ends moved, hubs ordered.

    The inputs and drawn functions come back with the copies at star wires (model-0220).
    """
    columns = replicate_terminals(all_columns, inputs.functions, inputs.connections)
    columns = replicate_boundaries(columns, unit_boundaries(model), inputs.functions, all_columns)
    fits = sheet_fits(drawn, inputs.profile, inputs.sheet, HEADROOM_LANES)
    columns = attach_replicas(columns, all_columns, drawn, inputs.connections, fits)
    far = FarInputs(
        drawn, inputs.connections, group_map(inputs.functions), free_pins(inputs, drawn)
    )
    columns = move_far_ends(columns, all_columns, far, fits)
    # model-0220: a star net's terminal stands at each of its wires, its own copy each
    copied = with_wire_copies(
        columns,
        drawn,
        inputs.functions,
        inputs.connections,
        # a harness line's conductor is drawn as the line, never at a copy
        {c.handle for c in star_wires(inputs.connections, inputs.functions, columns)}
        - line_reads(model).carried,
    )
    columns, drawn = copied.columns, copied.drawn
    inputs = replace(
        inputs,
        functions=copied.functions,
        connections=copied.connections,
        copies=tuple(sorted(copied.real.items())),
    )
    terminals, pairs, kept, stubbed = _terminal_wires(inputs)
    seats = stub_seats(model, inputs, columns, stubbed - kept)
    seats |= far_set_seats(columns, inputs.crossing, stubbed - kept)
    kept |= stubbed - {function for function, _ in seats} - kept
    columns = without_unwired_copies(columns, terminals, pairs, kept, seats)
    return inputs, drawn, hub_order(columns, inputs.functions, inputs.connections)


def _in_pin_order(
    columns: tuple[Column, ...], drawn: tuple[DrawnFunction, ...], inputs: StageInputs
) -> tuple[tuple[Column, ...], Power]:
    """layout-0264: a bundle's strands turn into the order of the box pins they land on.

    A row narrower than the bundle (a coil above it) keeps its lane. Also returns the power
    tuple it read, which the page run reads again.
    """
    landing: Power = (
        port_ranks(inputs.functions),
        *power_maps(inputs.power, inputs.item_north, inputs.item_south),
    )
    turned = lanes_in_pin_order(columns, function_landing(drawn, inputs.connections, landing))
    return turned, landing


def _terminal_wires(
    inputs: StageInputs,
) -> tuple[
    frozenset[Handle], tuple[tuple[Handle, Handle], ...], frozenset[Handle], frozenset[Handle]
]:
    """layout-0214: the terminals, each wire end (terminal, far), those kept and those stubbed.

    A terminal with a harness line, a rail end, a mate or a declared net keeps every copy; a
    crossing or off end is drawn at its stub's seat (`stub_seats`).
    """
    terminals = frozenset(s.function for s in inputs.functions if s.roles.terminal)
    ends = [(c.a, c.b) for c in inputs.connections] + [(c.b, c.a) for c in inputs.connections]
    wired = {r.port for c in inputs.carried for r in (c.a, c.b)}
    wired |= {e.ref.port for e in inputs.rail_ends}
    whole = wired | {r.port for g in inputs.net_groups for r in g.ports}
    stubs = {r.port for c in inputs.crossing for r in (c.a, c.b)} | {
        e.port for e in inputs.off_ends
    }
    kept = {s.function for s in inputs.functions for p in s.ports if p.port in whole}
    kept |= {f for mate in inputs.mates for f in (mate.a, mate.b)}
    stubbed = {s.function for s in inputs.functions for p in s.ports if p.port in stubs}
    pairs = tuple((a.function, b.function) for a, b in ends if a.function in terminals)
    reached = {a.function for a, _ in ends} | {f for mate in inputs.mates for f in (mate.a, mate.b)}
    reached |= stubbed | {s.function for s in inputs.functions for p in s.ports if p.port in wired}
    # model-0220: the wires went to copies, so a home no wire reaches is dropped (layout-0214)
    kept -= _copied_homes(inputs) - reached
    return terminals, pairs, frozenset(kept & terminals), frozenset(stubbed & terminals)


def _copied_homes(inputs: StageInputs) -> set[Handle]:
    """The terminals that have a copy at a wire (`inputs.copies` maps each copy to its home)."""
    copy_specs = {s.function for s in inputs.functions}
    return {home for copy, home in inputs.copies if copy in copy_specs and home in copy_specs}


def kept_terminals(inputs: StageInputs) -> frozenset[Handle]:
    """layout-0214: the terminals that keep every copy, a stubbed one too."""
    _, _, kept, stubbed = _terminal_wires(inputs)
    return kept | stubbed


def free_pins(inputs: StageInputs, drawn: tuple[DrawnFunction, ...]) -> frozenset[Handle]:
    """layout-0208: the channel pins whose box side `box_sides` turns toward their partners."""
    power = (
        port_ranks(inputs.functions),
        *power_maps(inputs.power, inputs.item_north, inputs.item_south),
    )
    turning = {one.function: turning_ports(one, power) for one in drawn}
    return frozenset(
        p.port
        for one in drawn
        for p in one.ports
        if is_channel(one, p.port) and p.port in turning[one.function]
    )


def arranged(
    model: Model, inputs: StageInputs, drawn: tuple[DrawnFunction, ...]
) -> tuple[
    StageInputs,
    tuple[DrawnFunction, ...],
    Power,
    tuple[Column, ...],
    tuple[Column, ...],
    tuple[Finding, ...],
]:
    """Stage 2: the columns of the run; the drawn functions and ranks gain the copies at wires."""
    tie_key = terminal_sort_keys(model, inputs.functions)
    # layout-0215: a device chain is one column of its own, out of discovery
    devices = device_columns(inputs.device_chains, inputs.functions)
    ranks = port_ranks(inputs.functions)
    discovered = (*discovered_columns(model, inputs, drawn, ranks, tie_key), *devices)
    crossing = set(inputs.crossing)
    inputs = replace(inputs, connections=tuple(c for c in inputs.connections if c not in crossing))
    chained, column_findings = chained_columns(inputs, drawn, discovered)
    all_columns, chains = ordered_columns(inputs, drawn, chained + discovered, tie_key)
    inputs = replace(
        inputs,
        connections=inline_exits(inputs.connections, all_columns, inputs.functions, drawn),
        terminal_chains=chains,
    )
    inputs, drawn, columns = replicated_columns(model, inputs, drawn, all_columns)
    columns, landing = _in_pin_order(columns, drawn, inputs)
    all_columns, columns = in_key_order(all_columns, columns)
    # layout-0214: a hint on a group whose every copy went names nothing left to draw
    gone = emptied_groups(all_columns, columns) | loose_groups(inputs.loose, columns)
    inputs = replace(inputs, hints=without_groups(inputs.hints, gone))
    return inputs, drawn, landing, all_columns, columns, column_findings
