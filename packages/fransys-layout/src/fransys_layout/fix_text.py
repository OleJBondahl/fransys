"""The `fix` of a layout finding: its code's template filled with the finding's values.

The stages that raise findings are imported by `lint`, so the code modules load lazily, on the
first call.
"""

from functools import cache

lazy from fransys_model.kernel import CodeInfo
lazy from fransys_model.vocab import FINDING_CODES as MODEL_CODES

lazy from .lint import codes_defects, codes_design, codes_design_more


@cache
def _by_code() -> dict[str, CodeInfo]:
    # the diagram engine raises DIAGRAM_* codes that the model registers
    infos = (
        *MODEL_CODES,
        *codes_defects.FINDING_CODES,
        *codes_design.FINDING_CODES,
        *codes_design_more.FINDING_CODES,
    )
    return {info.code: info for info in infos}


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return _by_code()[code].filled(**values)
