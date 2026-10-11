"""Step 4: `references` on one placing attempt's planned and stacked pages."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.exempt import ExemptInputs, boundary_exempt
from fransys_layout.stages.references import ReferenceInputs, black_box_sets, references

from .read.location_paths import location_paths
from .read.units import black_box_reads

if TYPE_CHECKING:
    from fransys_layout.stages.exempt import UnitNesting
    from fransys_layout.stages.references import References
    from fransys_layout.stages.references.types import Seating
    from fransys_model.kernel import Finding, Id, Model

    from .read import StageInputs


def decide(
    model: Model,
    inputs: StageInputs,
    nesting: UnitNesting,
    seating: Seating,
) -> tuple[References, tuple[Finding, ...]]:
    """Step 4: `references` on one placing attempt's planned and stacked pages."""
    exempt = boundary_exempt(
        ExemptInputs(
            inputs.connections, inputs.net_groups, inputs.functions, seating.plans, seating.seats
        ),
        nesting,
    )
    return references(_reference_inputs(model, inputs, seating, exempt, nesting.nested))


def _unit_maps(
    inputs: StageInputs, seating: Seating
) -> tuple[dict[Id[Any], Id[Any] | None], dict[int, Id[Any] | None]]:
    """Each function's unit, and each drawing set's own unit."""
    unit_of = {spec.function: spec.unit for spec in inputs.functions}
    set_unit = {plan.drawing_set: plan.unit for plan in seating.plans}
    return unit_of, set_unit


def _reference_inputs(
    model: Model,
    inputs: StageInputs,
    seating: Seating,
    exempt: frozenset[tuple[Id[Any], int]],
    nested: frozenset[Id[Any] | None],
) -> ReferenceInputs:
    """Step 4's `ReferenceInputs`: `inputs`, the planned pages and what it reads of `model`."""
    unit_of, set_unit = _unit_maps(inputs, seating)
    outward = black_box_sets(
        inputs.functions, seating.seats, unit_of, set_unit, black_box_reads(model, nested)
    )
    return ReferenceInputs(
        sheet=inputs.sheet,
        profile=inputs.profile,
        connections=inputs.connections,
        net_groups=inputs.net_groups,
        functions=inputs.functions,
        seating=seating,
        location_paths=location_paths(model, seating.plans),
        exempt=exempt,
        crossing=inputs.crossing,
        off_texts=inputs.off_texts,
        off_ends=inputs.off_ends,
        outward=outward,
        chains=inputs.terminal_chains,
        power={one.port: one for one in inputs.power},
        rail_ends=inputs.rail_ends,
    )
