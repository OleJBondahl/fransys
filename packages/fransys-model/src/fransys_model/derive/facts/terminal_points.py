"""How many conductors a terminal point takes and how many land on it (R1266, R1268)."""

from collections import Counter

from fransys_model.derive.facts.rating_index import function_block
from fransys_model.derive.facts.roles import conductor_role
from fransys_model.elecdef import Connection
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import conductors
lazy from fransys_model.vocab.core import Function, Port


def conductors_per_point(model: Model, function: Id[Function]) -> int:
    """The conductors each point of a terminal function takes: its part's `Connection.conductors_per_clamp`, else 1.

    Owner 2026-10-29: "Part states capacity". An unstated count is one (R1268).
    """
    block = function_block(model, function)
    return (block.conductors_per_clamp or 1) if isinstance(block, Connection) else 1


@digest_cached(DIGEST_CACHE_SIZE)
def point_conductors(model: Model) -> frozendict[Id[Port], int]:
    """Per port, the wires and cable cores that end on it; a bridge counts none."""
    ends = Counter(end for c in conductors(model).values() if conductor_role(model, c.id).carries for end in (c.a, c.b))
    return frozendict(ends)
