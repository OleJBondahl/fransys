"""What a function's facts say about its default symbol: its rest state and its protection type.

Both feed `symbol_defaults.default_symbol` (decision layout-0105); neither is a rule of its own.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import link_state
from fransys_model.vocab import pole_order
from fransys_model.vocab.enums import LinkKind
from fransys_model.vocab.tables import function_templates, internal_links, port_templates

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function


def function_rest(model: Model, function: Function) -> str | None:
    """`link_state` of the template's first switched link in pole order; None with no such link."""
    own = {t.id: t for t in port_templates(model).values() if t.function == function.template}
    switched = [
        link
        for link in internal_links(model).values()
        if link.kind is LinkKind.SWITCHED and link.a in own and link.b in own
    ]
    if not switched:
        return None
    ends = {end.id for end in pole_order(switched, own)[0].ends}
    first = next(link for link in switched if {link.a, link.b} == ends)
    return link_state(model, function.id, first.id)


def protection_type(model: Model, template: Id[Any] | None) -> str | None:
    """The function template's protection type as its string value, None without one."""
    found = None if template is None else function_templates(model)[template].protection_type
    return None if found is None else found.value
