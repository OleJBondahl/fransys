"""The row of `pole_gangs`: one `d.poles` group drawn as one multi-pole symbol."""

from fransys_model.kernel import value
lazy from fransys_model.kernel import Id
lazy from fransys_model.layout import PoleGroup
lazy from fransys_model.vocab.core import Function, Port


@value
class PolePort:
    """One port of a gang and the pole it is: member k's ports are pole k."""

    port: Id[Port]
    pole: int


@value
class PoleGang:
    """A pole group whose members are all drawn: `lead` draws it, member k is pole k."""

    group: Id[PoleGroup]
    lead: Id[Function]
    members: tuple[Id[Function], ...]
    selector: bool
    poles: int
    pole_of: tuple[PolePort, ...]
