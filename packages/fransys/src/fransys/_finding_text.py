"""The text of a finding: its subjects printed as names, and its one `CODE (severity):` head."""

from fransys_model.derive.numbering_pins import subject_text
from fransys_model.kernel import Finding, Model, describe

from ._codes import BY_CODE


def described(finding: Finding, model: Model) -> str:
    """`describe` with each subject printed by `subject_text` (BUILD-MESSAGES M5)."""
    names = {s: text for s in finding.subjects if (text := subject_text(model, s)) is not None}
    return describe(finding, model, names)


def headed(finding: Finding) -> str:
    """The finding's text under one `CODE (severity):` head: a described message has it already."""
    head = f"{finding.code} ({finding.severity.value}): "
    return finding.message if finding.message.startswith(head) else head + finding.message


def fix_lines(finding: Finding) -> list[str]:
    """The code's fix and guide anchor from its `CodeInfo`, as two lines (BUILD-MESSAGES M2).

    A code with no registry entry gives none.
    """
    info = BY_CODE.get(finding.code)
    return [] if info is None else [f"  fix: {info.fix}", f"  see: {info.see}"]
