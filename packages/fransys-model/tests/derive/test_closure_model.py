"""What net closure joins and what it leaves apart."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.vocab import closure as vocab_closure
from fransys_model.vocab.enums import LinkKind
lazy from fransys_model.vocab.core import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Id


def _fuse(kind: LinkKind, *names: str) -> tuple[Plant, dict[str, tuple[Id[Port], Id[Port]]]]:
    """A part whose two pins are linked as `kind`, and one instance of it per name."""
    plant = Plant()
    part, template, first, second = plant.relay_part()
    plant.link(first, second, kind)
    ports = {}
    for name in names:
        function = plant.function(plant.item(name, part=part.id), "fn", template=template.id)
        ports[name] = (
            plant.port(function, "1", template=first.id),
            plant.port(function, "2", template=second.id),
        )
    return plant, ports


def test_condition_needs_nothing_for_a_both_link() -> None:
    """A switched link of a non-contact function is `link_state` `"both"`: no condition."""
    plant, _ports = _fuse(LinkKind.SWITCHED, "g1")
    model = plant.model()
    (group,) = vocab_closure.link_groups(model, frozenset({LinkKind.SWITCHED}))
    assert vocab_closure._condition(model, group) == vocab_closure._ALWAYS


# ---- the shape of the result -------------------------------------------------------------


# ---- the cache ---------------------------------------------------------------------------
