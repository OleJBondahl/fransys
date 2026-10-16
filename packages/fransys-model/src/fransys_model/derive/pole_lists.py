"""The poles of a function from its own port templates: the one gathering of its pole links.

A function with no pole link pairs its pins by `unlinked_poles` (model-0128), earth pins left out.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.roles import is_pe_pin, link_role
from fransys_model.vocab import pole_order, unlinked_poles
from fransys_model.vocab.tables import internal_links, port_templates

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Pole
    from fransys_model.vocab.templates import PortTemplate

__all__ = ["poles_of"]


def poles_of(model: Model, own: Iterable[Id[PortTemplate]]) -> tuple[Pole, ...]:
    """The poles of a function whose port templates are `own`, in pole order."""
    templates = {t: port_templates(model)[t] for t in own}
    links = [
        link
        for link in internal_links(model).values()
        if link.a in templates and link.b in templates
    ]
    found = pole_order((link for link in links if link_role(model, link.id).pole), templates)
    pins = (t for key, t in templates.items() if not is_pe_pin(model, key))
    return found or unlinked_poles(pins)
