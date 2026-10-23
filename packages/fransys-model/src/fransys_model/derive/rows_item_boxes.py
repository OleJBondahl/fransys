"""The row shapes of `derive.item_box_views`: its input candidate and its item-view output."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Function, Item, Port


@value
class BoxCandidate:
    """One drawn function offered to `item_box_views`; the caller computes every flag once.

    `boxed`: no symbol names it (a PLC channel or a function no rule or choice draws). `symbol`:
    its first authored choice, `""` for none. `symbol_ports`: that symbol's port bound to each of
    `ports`, parallel to `ports`, empty without a choice. a pin view's `function` is its port's id.
    """

    function: Id[Function]
    item: Id[Item]
    key: tuple[str, ...]
    band: str
    plc_channel: bool
    pin: bool
    boxed: bool
    ports: tuple[Id[Port], ...]
    symbol: str
    symbol_ports: tuple[str, ...]


@value
class BoxPort:
    """A port of an item view: its printed box name and its rank in the box."""

    function: Id[Function]
    port: Id[Port]
    name: str
    rank: int


@value
class ItemBoxView:
    """An item drawn as one generic box, or (`lone`) a lone unwired PLC channel drawn as its own.

    `members` are the functions in the box, in candidate order; `apart` draw on their own.
    `lead` has the least key. `kind` is the band's kind. `named`: authored choices all name one
    symbol, so that symbol draws the box, else the generic box does. `lone` rows have no ports.
    """

    item: Id[Item]
    members: tuple[Id[Function], ...]
    apart: tuple[Id[Function], ...]
    lead: Id[Function]
    kind: str
    named: bool
    lone: bool
    ports: tuple[BoxPort, ...]
