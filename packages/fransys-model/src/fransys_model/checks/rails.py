"""Validator: a rail group has a potential, no fuse, and is joined inside its unit to any other group of its potential (R885, R3336)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.closure import link_groups
from fransys_model.derive.facts.potentials import rail_potential
from fransys_model.derive.facts.rail_reach import rails_joined_in_unit
from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items, rail_groups

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Item, RailGroup, Unit

RAIL_DUPLICATE_POTENTIAL: Final[str] = "RAIL_DUPLICATE_POTENTIAL"
RAIL_WITHOUT_POTENTIAL: Final[str] = "RAIL_WITHOUT_POTENTIAL"
RAIL_ON_FUSED: Final[str] = "RAIL_ON_FUSED"
_FIX: Final[str] = "flag one strip per potential across this unit boundary until unflagged boundary strips draw with wires (UTW-G1)"


def _where(model: Model, group: RailGroup) -> str:
    origin = model.origins[group.id]
    return f"rail group {ref(group)} ({origin.file}:{origin.line})"


def _fused_text(model: Model, terminal: Id[Item]) -> str:
    strip = ref(items(model)[strip_of(model, terminal) or terminal])
    return f"the rail group on strip {strip} holds a fused terminal (its part has a protective link): flag the supply side of the fuse, not {strip}"


def _own_findings(model: Model, group: RailGroup, fused: set[Id[Item]]) -> list[Finding]:
    """The findings one group raises alone: no potential, or a fused terminal."""
    if rail_potential(model, group) is None:
        return [finding(RAIL_WITHOUT_POTENTIAL, (group.id,), f"{_where(model, group)} carries no potential: declare the potential first")]
    hit = next((t for t in group.terminals if t in fused), None)
    return [] if hit is None else [finding(RAIL_ON_FUSED, (group.id,), _fused_text(model, hit))]


def _duplicate(model: Model, group: RailGroup, other: RailGroup, potential: str) -> Finding:
    both = f"{_where(model, group)} and {_where(model, other)} are both the {potential} rail of one unit"
    return finding(RAIL_DUPLICATE_POTENTIAL, (other.id, group.id), f"{both}, and no wiring inside the unit joins them: {_FIX}")


def check_rails(model: Model) -> tuple[Finding, ...]:
    """Error on a rail group with no potential, on a fused terminal, and on two of one potential in a unit not joined inside it (R3336)."""
    fused = {g.item for g in link_groups(model, lambda role: role.protective)}
    seen: dict[tuple[Id[Unit] | None, str], RailGroup] = {}
    found = []
    for group in rail_groups(model).values():
        found += _own_findings(model, group, fused)
        if (potential := rail_potential(model, group)) is None:
            continue
        unit = item_unit(model, group.terminals[0])
        other = seen.setdefault((unit, potential), group)
        if other is not group and not rails_joined_in_unit(model, group, other):
            found.append(_duplicate(model, group, other, potential))
    return ordered(found)
