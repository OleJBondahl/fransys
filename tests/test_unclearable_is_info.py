"""A drawing defect no consumer action clears is INFO, with Fransys's own text (layout-0252).

The codes whose fix is `COULD_NOT_DRAW` are the render-stage WARNINGs whose `who` is Fransys.
Each is INFO in its `CodeInfo`, the one home of its severity. Every other layout WARNING keeps a
"""

from fransys_layout.lint.codes import FINDING_CODES
from fransys_layout.lint.codes_defects import COULD_NOT_DRAW
from fransys_model.kernel import Severity

TEXT = "Fransys could not draw this cleanly; please report it with the smallest model"
UNCLEARABLE = {info.code for info in FINDING_CODES if info.fix == TEXT}


def test_every_unclearable_code_is_info_with_the_text() -> None:
    infos = {info.code: info for info in FINDING_CODES}
    assert COULD_NOT_DRAW == TEXT
    assert len(UNCLEARABLE) == 2
    for code in UNCLEARABLE:
        assert infos[code].severity is Severity.INFO, code


def test_no_warning_a_consumer_can_clear_is_touched() -> None:
    """Every layout WARNING outside the list names a consumer or author action."""
    for info in FINDING_CODES:
        if info.code not in UNCLEARABLE and info.severity is Severity.WARNING:
            assert info.who != "Fransys", info.code
