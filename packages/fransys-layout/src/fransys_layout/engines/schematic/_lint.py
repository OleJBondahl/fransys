"""Stage 9: the lint over the finished layout."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.lint import (
    HarnessInk,
    check_coherence,
    check_members,
    check_nowhere,
    lint_chains,
    lint_geometry,
)
from fransys_layout.lint.chains import StageRecords

if TYPE_CHECKING:
    from fransys_layout.stages import Column, DrawnFunction, Layout
    from fransys_model.kernel import Finding

    from .read import StageInputs


@dataclass(frozen=True, slots=True)
class Members:
    """What the member check reads: the connections and net groups before the stars, the exempt."""

    connections: tuple[Any, ...]
    net_groups: tuple[Any, ...]
    exempt: frozenset[tuple[Any, int]]


@dataclass(frozen=True, slots=True)
class LintScene:
    """What stage 9 lints: the `layout` with its `columns` and `drawn` functions, the `inputs`."""

    layout: Layout
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    inputs: StageInputs
    members: Members
    open_ends: frozenset[Any]
    ink: HarnessInk


def lint_findings(scene: LintScene) -> list[Finding]:
    """Stage 9: the geometry, chain, coherence and member findings of `scene.layout`."""
    layout, columns, drawn, inputs = scene.layout, scene.columns, scene.drawn, scene.inputs
    members, open_ends = scene.members, scene.open_ends
    findings = list(lint_geometry(layout, sheet=inputs.sheet, ink=scene.ink))
    findings.extend(
        lint_chains(
            layout,
            # HL1: a pin a line carries a conductor to is wired
            StageRecords(
                columns,
                drawn,
                (*inputs.connections, *inputs.carried),
                inputs.net_groups,
                inputs.mates,
            ),
            open_ends=open_ends,
        )
    )
    # R7 B4: star markers answer no cut decision
    paired = replace(layout, markers=tuple(m for m in layout.markers if not m.star))
    function_units = {spec.function: spec.unit for spec in inputs.functions}
    findings.extend(
        check_coherence(
            paired, inputs.connections, inputs.net_groups, drawn, function_units=function_units
        )
    )
    connections, net_groups = members.connections, members.net_groups
    missing = check_members(layout, connections, net_groups, drawn, members.exempt)
    findings.extend(missing)
    # a stubbed (crossing) conductor is covered by its stubs: the guard reads it too (rule 7)
    findings.extend(
        check_nowhere(layout, (*connections, *inputs.crossing), net_groups, drawn, missing)
    )
    return findings
