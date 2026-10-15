"""The poles of a function from its own port templates: the one gathering of its pole links.

A function with no pole link pairs its pins by `unlinked_poles` (model-0128), earth pins left out.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab import function_poles, unlinked_poles
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import internal_links, port_templates

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Pole
    from fransys_model.vocab.enums import FunctionKind
    from fransys_model.vocab.templates import PortTemplate

__all__ = ["poles_of"]


def poles_of(model: Model, kind: FunctionKind, own: Iterable[Id[PortTemplate]]) -> tuple[Pole, ...]:
    """The poles of a function of `kind` whose port templates are `own`, in pole order."""
    templates = {t: port_templates(model)[t] for t in own}
    links = [
        link
        for link in internal_links(model).values()
        if link.a in templates and link.b in templates
    ]
    found = function_poles(kind, links, templates)
    pins = (t for t in templates.values() if t.role is not PortRole.PE)
    return found or unlinked_poles(pins)
