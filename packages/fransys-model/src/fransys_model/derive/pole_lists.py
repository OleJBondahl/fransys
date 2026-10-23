"""The poles of a function from its own port templates: the one gathering of its pole links.

A function with no pole link falls back on its pins (`poles_of_template`, model-0128).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.part_poles import poles_of_template
from fransys_model.vocab.tables import function_templates, internal_links, port_templates

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Pole
    from fransys_model.vocab.templates import PortTemplate

__all__ = ["poles_of"]


def poles_of(model: Model, own: Iterable[Id[PortTemplate]]) -> tuple[Pole, ...]:
    """The poles of a function whose port templates are `own`, in pole order."""
    templates = [port_templates(model)[t] for t in own]
    if not templates:
        return ()
    kind = function_templates(model)[templates[0].function].kind
    return poles_of_template(kind, templates, internal_links(model).values())
