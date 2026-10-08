"""The records of a part-less external item (PATCH-0132 E2, E3): no template on any."""

from fransys_author._keys import scoped
from fransys_author.errors import AuthorError
from fransys_model.kernel import AuthoringKey, Id, Record, make_id
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

# The port name of the demo terminal part; layout's T2.21 port map holds the name too.
TERMINAL_OUTER = "external"
NEEDS_TAG = "an item with no part needs a tag: no part file gives its letter"


def check_partless(tag: str | None, *, external: bool, call: str) -> None:
    """Raise `AuthorError` when a call that gave no part is not an external item with a tag."""
    if not external:
        msg = f"{call}: part=None needs external=True; only equipment others supply has no part"
        raise AuthorError(msg)
    if tag is None:
        raise AuthorError(NEEDS_TAG)


def _function(item: Id[Item], key: AuthoringKey, name: str, kind: FunctionKind) -> Function:
    fkey = scoped(key, "fn", name)
    return Function(
        id=make_id(Function, fkey), key=fkey, item=item, template=None, name=name, kind=kind
    )


def _port(function: Function, name: str, role: PortRole) -> Port:
    pkey = scoped(function.key, "port", name)
    return Port(
        id=make_id(Port, pkey), key=pkey, function=function.id, template=None, name=name, role=role
    )


def terminal_records(key: AuthoringKey, parent: Id[Item]) -> tuple[Record, ...]:
    """A part-less terminal: its item, one terminal function and the one port `external`."""
    item = Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=parent,
        position=None,
        tag=None,
        description="",
    )
    function = _function(item.id, key, "terminal", FunctionKind.TERMINAL)
    return (item, function, _port(function, TERMINAL_OUTER, PortRole.EXTERNAL))


def box_records(item: Id[Item], key: AuthoringKey, pins: tuple[str, ...]) -> tuple[Record, ...]:
    """One generic function `box` of the item `key`, with a generic port per pin name."""
    if not pins or len(set(pins)) != len(pins):
        msg = f"pins= names each pin once, and at least one: {pins!r}"
        raise AuthorError(msg)
    function = _function(item, key, "box", FunctionKind.GENERIC)
    return (function, *(_port(function, pin, PortRole.GENERIC) for pin in pins))
