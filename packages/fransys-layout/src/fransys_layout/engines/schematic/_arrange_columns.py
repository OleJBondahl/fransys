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
from fransys_layout.stages.chains import ChainRecords, discover_chains
from fransys_layout.stages.far_ends import FarInputs, group_map, move_far_ends, sheet_fits
from fransys_layout.stages.pin_ends import pin_keyed
from fransys_layout.stages.replicate import replicate_boundaries, replicate_terminals
from fransys_layout.stages.terminal_rows import join_terminal_rows, terminal_chains
from fransys_layout.stages.types import Home

from .defaults import HEADROOM_LANES
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
    # A chain never gets a function discovery already placed.
    chain_claimed = {
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
    # An edge pin's face replica is not its home; its home column still comes below
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
            <= inputs.sheet.content_width
        ),
    )
    return rack_order(all_columns, inputs.functions), chains


def replicated_columns(
    model: Model,
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    all_columns: tuple[Column, ...],
) -> tuple[Column, ...]:
    """The columns with terminal, boundary and attached replicas, far ends moved, hubs ordered."""
    columns = replicate_terminals(all_columns, inputs.functions, inputs.connections)
    columns = replicate_boundaries(columns, unit_boundaries(model), inputs.functions, all_columns)
    fits = sheet_fits(drawn, inputs.profile, inputs.sheet, HEADROOM_LANES)
    columns = attach_replicas(columns, all_columns, drawn, inputs.connections, fits)
    far = FarInputs(drawn, inputs.connections, group_map(inputs.functions))
    columns = move_far_ends(columns, all_columns, far, fits)
    return hub_order(columns, inputs.functions, inputs.connections)


def arranged(
    model: Model, inputs: StageInputs, drawn: tuple[DrawnFunction, ...], rank_of: Mapping[Any, int]
) -> tuple[
    StageInputs,
    tuple[Column, ...],
    tuple[Column, ...],
    tuple[Finding, ...],
]:
    """Stage 2: the columns of the run."""
    tie_key = terminal_sort_keys(model, inputs.functions)
    discovered = discovered_columns(model, inputs, drawn, rank_of, tie_key)
    crossing = set(inputs.crossing)
    inputs = replace(inputs, connections=tuple(c for c in inputs.connections if c not in crossing))
    chained, column_findings = chained_columns(inputs, drawn, discovered)
    all_columns, chains = ordered_columns(inputs, drawn, chained + discovered, tie_key)
    inputs = replace(
        inputs,
        connections=inline_exits(inputs.connections, all_columns, inputs.functions, drawn),
        terminal_chains=chains,
    )
    columns = replicated_columns(model, inputs, drawn, all_columns)
    return inputs, all_columns, columns, column_findings
