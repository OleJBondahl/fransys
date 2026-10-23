"""The row shapes of `derive.connector_pin_views` and `derive.connector_pin_mates` (model-0199)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Function, Item, Port


@value
class PinView:
    """One pin of a connector function, drawn as a view of its own.

    `gender`: the connector facet's, `""` without one. `mate`: the equal-named pin of the mated
    connector, `None` without. `drawn`: the pin is kept. `elsewhere`: a kept unit-boundary pin no
    wire inside the drawing reaches, shown only in the parent's black box.
    """

    port: Id[Port]
    function: Id[Function]
    item: Id[Item]
    name: str
    gender: str
    mate: Id[Port] | None
    drawn: bool
    elsewhere: bool


@value
class PinMate:
    """Two equal-named pins of mated connectors: the upper (plug) side and the lower."""

    upper: Id[Port]
    lower: Id[Port]
