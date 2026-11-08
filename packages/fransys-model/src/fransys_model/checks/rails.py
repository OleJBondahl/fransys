"""Validator: a declared rail group has a potential, no fuse, and is the only one of its potential in a unit (R885)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.closure import link_groups
from fransys_model.derive.facts.potentials import rail_potential
from fransys_model.derive.facts.rail_reach import rail_scope
from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items, rail_groups

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Item, RailGroup

RAIL_DUPLICATE_POTENTIAL: Final[str] = "RAIL_DUPLICATE_POTENTIAL"
RAIL_WITHOUT_POTENTIAL: Final[str] = "RAIL_WITHOUT_POTENTIAL"
RAIL_ON_FUSED: Final[str] = "RAIL_ON_FUSED"


def _where(model: Model, group: RailGroup) -> str:
    origin = model.origins[group.id]
    return f"rail group {ref(group)} ({origin.file}:{origin.line})"


def _fused_text(model: Model, terminal: Id[Item]) -> str:
    strip = ref(items(model)[strip_of(model, terminal) or terminal])
    return f"the rail group on strip {strip} holds a fused terminal (its part has a protective link): flag the supply side of the fuse, not {strip}"


def check_rails(model: Model) -> tuple[Finding, ...]:
    """Error on a rail group with no power potential, on a fused terminal, and on two groups of one potential in one unit."""
    fused = {g.item for g in link_groups(model, lambda role: role.protective)}
    first = rail_scope(model)
    found = []
    for group in rail_groups(model).values():
        potential = rail_potential(model, group)
        if potential is None:
            found.append(finding(RAIL_WITHOUT_POTENTIAL, (group.id,), f"{_where(model, group)} carries no potential: declare the potential first"))
            continue
        if (hit := next((t for t in group.terminals if t in fused), None)) is not None:
            found.append(finding(RAIL_ON_FUSED, (group.id,), _fused_text(model, hit)))
        if (other := rail_groups(model)[first[item_unit(model, group.terminals[0]), potential]]) is not group:
            msg = f"{_where(model, group)} and {_where(model, other)} are both the {potential} rail of one unit: one group per potential"
            found.append(finding(RAIL_DUPLICATE_POTENTIAL, (other.id, group.id), msg))
    return ordered(found)
