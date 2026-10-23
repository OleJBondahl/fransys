"""The row shape of `derive.undrawn_functions` (model-0199)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Function


@value
class UndrawnFunctions:
    """The functions the old schematic engine leaves off the page, by why, each in id order.

    `loose`: nothing connected. `spare`: unused, so a spare.
    `idle`: a terminal on no connection, net group or mate. `elsewhere`: a boundary terminal that
    no wire inside reaches, kept only for the parent's black box.
    `accessory`: a function of an accessory declared open on purpose, whatever the profile says.
    """

    loose: tuple[Id[Function], ...]
    spare: tuple[Id[Function], ...]
    idle: tuple[Id[Function], ...]
    elsewhere: tuple[Id[Function], ...]
    accessory: tuple[Id[Function], ...]
