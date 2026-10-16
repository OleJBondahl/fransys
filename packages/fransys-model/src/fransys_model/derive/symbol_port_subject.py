"""The record a missing symbol port is reported against (decision 0018, model-0283, R92)."""

from typing import cast

from fransys_model.vocab.tables import functions, items, parts, port_templates
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Function, Item, Part, PortTemplate

__all__ = ["symbol_port_subject"]


def symbol_port_subject(
    model: Model, function: Id[Function] | Id[Item], port_name: str
) -> Id[PortTemplate] | Id[Part] | Id[Function] | Id[Item]:
    """The `PortTemplate` of `function`'s template named `port_name`, else its `Part`, else itself.

    `function` is a Function of the model, or the whole Item of a one-view draw (no template).
    """
    if function in items(model):
        item = items(model)[cast("Id[Item]", function)]
        template = None
    else:
        record = functions(model)[cast("Id[Function]", function)]
        item = items(model)[record.item]
        template = record.template
    if template is not None:
        for candidate in port_templates(model).values():
            if candidate.function == template and candidate.name == port_name:
                return candidate.id
    part = parts(model).get(item.part) if item.part is not None else None
    return part.id if part is not None else function
