"""The poles of a function from its own port templates: the one gathering of its pole links.

A function with no pole link falls back on its pins (`poles_of_template`, model-0128).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.part_poles import poles_of_template
from fransys_model.derive.facts.roles import function_role
from fransys_model.vocab.markings import pole_order, poles_by_role
from fransys_model.vocab.tables import function_templates, internal_links, port_templates
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab import Function, Pole

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id
    from fransys_model.vocab.templates import PortTemplate

__all__ = ["function_poles", "poles_of"]


def poles_of(model: Model, own: Iterable[Id[PortTemplate]]) -> tuple[Pole, ...]:
    """The poles of a function whose port templates are `own`, in pole order."""
    templates = [port_templates(model)[t] for t in own]
    if not templates:
        return ()
    kind = function_templates(model)[templates[0].function].kind
    return poles_of_template(kind, templates, internal_links(model).values())


def function_poles(model: Model, function: Function) -> tuple[Pole, ...]:
    """The poles of a function: its pole links by role, else every link of its template, in pole order."""
    own = {t.id: t for t in port_templates(model).values() if t.function == function.template}
    links = [k for k in internal_links(model).values() if k.a in own and k.b in own]
    return poles_by_role(function_role(model, function.id), links, own) or pole_order(links, own)
