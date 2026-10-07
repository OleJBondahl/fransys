"""Whether a connector ends a harness line: one fact, read from the ends row (model-0176)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

from .harness_line_ends import harness_line_ends
from .line_fact import line_conductors

__all__ = ["connector_at_line_end"]


@digest_cached(DIGEST_CACHE_SIZE)
def _at_line_ends(model: Model) -> frozenset[Id[Function]]:
    """The connector functions of every drawn line's ends: a plug, its mate, a fan-out's pins'."""
    found: set[Id[Function]] = set()
    for subject in line_conductors(model):
        for end in harness_line_ends(model, subject):
            found.update(f for f in (end.plug, end.mates) if f is not None)
            found.update(ports(model)[port].function for port in end.ports)
    return frozenset(found)


def connector_at_line_end(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a plug, the function a plug mates, or a fan-out pin's function.

    Read from `harness_line_ends` of the lines `draws_as_line` holds, and nothing else. HL6,
    HL12, HL13 and the side hint's WARNING call it and never ask again. A connector at no line
    gives `False`.
    """
    return function in _at_line_ends(model)
