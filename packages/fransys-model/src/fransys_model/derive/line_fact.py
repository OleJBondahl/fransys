"""Whether a cable or harness draws as a harness line: HL1's one test (model-0180)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.membership import is_harness
from fransys_model.vocab.tables import conductors, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item

from .wire_harness import harness_of_wire

__all__ = ["draws_as_line", "line_conductors"]


def _owner(model: Model, carrier: Id[Item]) -> Id[Item]:
    """A cable's line is its harness's when it has one, else its own."""
    parent = items(model)[carrier].parent
    return parent if parent is not None and is_harness(model, parent) else carrier


@digest_cached(DIGEST_CACHE_SIZE)
def line_conductors(model: Model) -> frozendict[Id[Item], tuple[Id[Conductor], ...]]:
    """Each line's owner with the conductors its line carries, for owners with two or more.

    The owner is a harness, or a cable on no harness. Cores count for their cable's owner and a
    single wire for its harness (`harness_of_wire`). Conductors are sorted by id.
    """
    found: dict[Id[Item], set[Id[Conductor]]] = {}
    for conductor in conductors(model).values():
        if conductor.carrier is not None:
            owner: Id[Item] | None = _owner(model, conductor.carrier)
        elif conductor.kind is ConductorKind.WIRE:
            owner = harness_of_wire(model, conductor.id)
        else:
            owner = None
        if owner is not None:
            found.setdefault(owner, set()).add(conductor.id)
    return frozendict(
        {owner: tuple(sorted(ids)) for owner, ids in sorted(found.items()) if len(ids) > 1}
    )


def draws_as_line(model: Model, item: Id[Item]) -> bool:
    """Whether `item`, a cable or a harness, draws as a harness line.

    True when its line carries two or more conductors, cores and single wires together; a cable
    on a harness answers for its harness. Layout, `connector_at_line_end` and `off_stub_text`
    read it and never count again. Any other item, or an id that is no item, gives `False`.
    """
    if item not in items(model):
        return False
    return _owner(model, item) in line_conductors(model)
