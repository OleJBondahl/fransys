"""The values `build` takes besides the model: the symbol kit, and the error it raises.

The caller picks each function's symbol once (el-0002); the builder never chooses a symbol.
"""

from dataclasses import dataclass
from typing import NoReturn, Protocol

from fransys_model.kernel import Id
from fransys_model.vocab import Function, Port

__all__ = ["Pick", "ProblemError", "Rect", "SymbolKit", "refuse"]


@dataclass(frozen=True, slots=True)
class Pick:
    """The symbol that draws one function.

    `ports` maps each model port of the function, and of each `members` function, to a port
    name of the symbol. `members` are the other functions of a pole group drawn into this
    symbol; a member has no symbol of its own.
    """

    key: str
    poles: int
    ports: frozendict[Id[Port], str]
    members: tuple[Id[Function], ...] = ()


SymbolKit = frozendict[Id[Function], Pick]


class ProblemError(ValueError):
    """An input the builder cannot turn into a problem: names the thing and the fix."""

    def __init__(self, subject: str, fix: str) -> None:
        super().__init__(f"{subject}: {fix}")
        self.subject = subject
        self.fix = fix


def refuse(subject: str, fix: str) -> NoReturn:
    """Raise `ProblemError` for `subject` with the `fix`."""
    raise ProblemError(subject, fix)


class Rect(Protocol):
    """Any box with an origin and a size: a geometry box or a measured extent."""

    @property
    def x(self) -> int: ...
    @property
    def y(self) -> int: ...
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
