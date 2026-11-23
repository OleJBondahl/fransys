"""The A3 and A2 sheets of the shipped settings: the one test-side home of the sheet numbers."""

from decimal import Decimal
from functools import cache
from typing import cast

import fransys as fr

from fransys_model.layout import SheetFormat, sheet_format_record

__all__ = ["a2", "a3"]


@cache
def _sheet(name: str) -> SheetFormat:
    table = cast("dict[str, int | str]", cast("dict[str, object]", fr.settings().paper["formats"])[name])
    numbers = {k: int(cast("int", v)) for k, v in table.items() if k != "name"}
    return sheet_format_record(("build", "paper", name), str(table["name"]), numbers, Decimal("2.5"))


def a3() -> SheetFormat:
    """The shipped A3 landscape sheet."""
    return _sheet("A3")


def a2() -> SheetFormat:
    """The shipped A2 landscape sheet."""
    return _sheet("A2")
