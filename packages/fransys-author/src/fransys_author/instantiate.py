"""Stamping an `Item`, its functions and ports from a `PartBundle` (author-0070; design/vocabulary.md 7)."""

from fransys_model.kernel import AuthoringKey, Id, Record, make_id
from fransys_model.vocab import Function, Item, PartBundle, Port, PortTemplate

__all__ = ["instantiate"]


def _port(function: Function, template: PortTemplate) -> Port:
    key = (*function.key, "port", template.name)
    return Port(
        id=make_id(Port, key),
        key=key,
        function=function.id,
        template=template.id,
        name=template.name,
        boundary=template.boundary,
        # model-0053: the part's pin marking travels with the port
        marking=template.marking,
        pin_role=template.pin_role,
        source_row=template.source_row,
    )


def instantiate(  # noqa: PLR0913 -- exact signature fixed by this WP's contract
    bundle: PartBundle,
    item_key: AuthoringKey,
    *,
    tag: str | None = None,
    parent: Id[Item] | None = None,
    position: int | None = None,
    description: str = "",
    installed: bool = True,
) -> tuple[Record, ...]:
    """Stamp one `Item`, a `Function` per function template and a `Port` per port template, in id order.

    Keys are `(*item_key, "fn", name)` and `(*function_key, "port", name)`; `tag` `None` leaves it to numbering.
    Raises `SchemaError` when `item_key` or a template name is not a valid key segment.
    """
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=bundle.part.id,
        parent=parent,
        position=position,
        tag=tag,
        description=description,
        installed=installed,
    )
    stamped: list[Record] = [item]
    for function_template in bundle.function_templates:
        key = (*item.key, "fn", function_template.name)
        function = Function(
            id=make_id(Function, key),
            key=key,
            item=item.id,
            template=function_template.id,
            name=function_template.name,
            kind=function_template.kind,
        )
        stamped.append(function)
        stamped.extend(_port(function, port_template) for port_template in bundle.port_templates if port_template.function == function_template.id)
    return tuple(sorted(stamped, key=lambda record: record.id))
