"""The values `build` takes besides the model: the symbol kit, and the error it raises.

The caller picks each function's symbol once (el-0002); the builder never chooses a symbol.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

lazy from fransys_model.kernel import Id

if TYPE_CHECKING:
    from fransys_model.vocab import Function, Port

__all__ = ["Pick", "PortMissingError", "ProblemError", "SymbolKit", "refuse"]


@dataclass(frozen=True, slots=True)
class Pick:
    """The symbol that draws one function.

    `ports` maps each port of the function and of its pole-group `members` to a symbol port name.
    """

    key: str
    poles: int
    ports: frozendict[Id[Port], str]
    members: tuple[Id[Function], ...] = ()


type PickKey = Id[Function] | Id[Port]
SymbolKit = frozendict[PickKey, Pick]


class ProblemError(ValueError):
    """An input the builder cannot turn into a problem: names the thing, the fix and its key.

    `key` is the problem key el gave the thing (a symbol id), `None` for a thing with none.
    """

    def __init__(self, subject: str, fix: str, key: str | None = None) -> None:
        super().__init__(f"{subject}: {fix}")
        self.subject = subject
        self.fix = fix
        self.key = key


class PortMissingError(ProblemError):
    """A model port that has no free port on the symbol chosen for its function (SYMBOL_PORT_MISSING)."""

    def __init__(self, function: Id[Function], port_name: str, symbol: str, key: str | None) -> None:
        super().__init__(f"function {function} port {port_name}", f"no free port on symbol {symbol}", key)
        self.function = function
        self.port_name = port_name
        self.symbol = symbol


def refuse(subject: str, fix: str, key: str | None = None) -> NoReturn:
    """Raise `ProblemError` for `subject` with the `fix`; `key` is the symbol id of the thing."""
    raise ProblemError(subject, fix, key)
