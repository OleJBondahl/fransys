"""layout-0245: the second power pass's findings replace the first's for the ports it redid."""

from typing import Any

from fransys_layout.stages.texts.place_texts import LABEL_UNPLACED
from fransys_layout.stages.texts.power_lead import POWER_SYMBOL_UNPLACED
from fransys_layout.stages.texts.power_moved import PowerRedo
from fransys_model.kernel import Finding, Id, Severity

MOVED: Any = Id(kind="port", value="moved")
STILL: Any = Id(kind="port", value="still")


def _finding(code: str, port: Any) -> Finding:
    return Finding(code=code, severity=Severity.WARNING, subjects=(port,), message=code)


def test_a_redone_ports_power_findings_are_the_second_passes_and_the_rest_are_kept() -> None:
    old = [_finding(POWER_SYMBOL_UNPLACED, MOVED), _finding(LABEL_UNPLACED, STILL)]
    new = _finding(LABEL_UNPLACED, MOVED)
    other = _finding("SOMETHING_ELSE", MOVED)
    redo = PowerRedo(frozenset({MOVED}), (new,))
    assert redo.over([*old, other]) == [old[1], other, new]
