"""Layout errors: structural problems, raised and never silenced (docs/design/geometry.md 5.4).

Layout problems of a half-finished design are not here: a stage returns a kernel
`Finding` instead of raising.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import ModelError

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Record


class LayoutError(ModelError):
    """Base of everything this repo raises."""


class UnknownSymbolError(LayoutError):
    """A symbol key is not in the symbol library; no placeholder is ever substituted."""

    def __init__(self, message: str, *, key: str) -> None:
        """Record the symbol `key` that was not found."""
        super().__init__(message)
        self.key = key


class GeometryError(LayoutError):
    """A library coordinate is off the drawing grid (0.125 M), or a box has a negative size."""


class SymbolPortError(LayoutError):
    """A model port has no port of that name on the chosen symbol, after `port_map`."""

    def __init__(self, message: str, *, function: Id[Record], port_name: str) -> None:
        """Record the drawn `function` (an `Item`'s id for a whole-item symbol) and `port_name`."""
        super().__init__(message)
        self.function = function
        self.port_name = port_name


class HintError(LayoutError):
    """An authored layout hint contradicts the model or another hint."""

    def __init__(self, message: str, *, subjects: tuple[Id[Any], ...]) -> None:
        """Record the hint and the records it contradicts."""
        super().__init__(message)
        self.subjects = subjects
