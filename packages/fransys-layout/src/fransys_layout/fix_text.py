"""The `fix` of a layout finding: its code's template filled with the finding's values.

The stages that raise findings are imported by `lint`, so the code modules load lazily, on the
first call.
"""

from functools import cache
from typing import Any
lazy from collections.abc import Iterable

lazy from fransys_model.kernel import CodeBook, Finding, Id
lazy from fransys_model.vocab import FINDING_CODES as MODEL_CODES

lazy from .lint import codes_defects, codes_design


@cache
def _book() -> CodeBook:
    # the diagram engine raises DIAGRAM_* codes that the model registers
    return CodeBook(*MODEL_CODES, *codes_defects.FINDING_CODES, *codes_design.FINDING_CODES)


def finding(code: str, subjects: Iterable[Id[Any]], message: str, **fix_values: str) -> Finding:
    """The `Finding` of `code`: its one severity, its fix filled from `fix_values`."""
    return _book().finding(code, subjects, message, **fix_values)
