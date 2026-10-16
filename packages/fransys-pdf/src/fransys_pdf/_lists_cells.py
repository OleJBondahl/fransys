"""The cell and column helpers the list tables share: header text, cell markup, widths."""

from typing import TYPE_CHECKING

from fransys_model.derive import CELL_SEPARATOR, cell_parts, cell_text

from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Iterable


def _cell_typst(value: object) -> str:
    """`value` as one table cell's Typst markup: tuple items in unbreakable boxes (pdf-0013)."""
    match value:
        case tuple():
            parts = cell_parts(value)
            if not parts:
                return f"text({literal('')})"
            return f" + text({literal(CELL_SEPARATOR)}) + ".join(
                f"box(text({literal(part)}))" for part in parts
            )
        case _:
            return f"text({literal(cell_text(value))})"


def _kept_columns(rows: Iterable[tuple[object, ...]], count: int) -> tuple[int, ...]:
    """The indexes of the `count` columns with a non-empty `cell_text` in some row (pdf-0011)."""
    materialised = list(rows)
    return tuple(i for i in range(count) if any(cell_text(row[i]) for row in materialised))


def _widths(wide: list[bool]) -> list[str]:
    """`1fr` per `True`, else `auto`; the last is `1fr` if none is, to span the page (pdf-0008)."""
    widths = ["1fr" if flag else "auto" for flag in wide]
    if widths and "1fr" not in widths:
        widths[-1] = "1fr"
    return widths
