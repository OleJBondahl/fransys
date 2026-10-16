"""The text of a finding: its subjects printed as names, and its one `CODE (severity):` head."""

from typing import Any

from fransys_model.derive.docs_site import finding_url
from fransys_model.derive.numbering_pins import subject_text
from fransys_model.kernel import DescribedFinding, Finding, Id, Model, describe, describe_parts

from ._codes import BY_CODE
from ._version import __version__


def _names(finding: Finding, model: Model) -> dict[Id[Any], str]:
    return {s: text for s in finding.subjects if (text := subject_text(model, s)) is not None}


def described(finding: Finding, model: Model) -> str:
    """`describe` with each subject printed by `subject_text` (BUILD-MESSAGES M5)."""
    return describe(finding, model, _names(finding, model))


def described_parts(finding: Finding, model: Model) -> DescribedFinding:
    """`described` kept as its head and subject texts, so no caller splits the joined text."""
    return describe_parts(finding, model, _names(finding, model))


def headed(finding: Finding) -> str:
    """The finding's text under one `CODE (severity):` head: a described message has it already."""
    head = f"{finding.code} ({finding.severity.value}): "
    return finding.message if finding.message.startswith(head) else head + finding.message


def fix_lines(finding: Finding) -> list[str]:
    """The code's fix and the URL of its row on this release's findings page, as two lines.

    BUILD-MESSAGES M2, DOCS-FOR-AGENTS D6. A code with no registry entry gives none.
    """
    info = BY_CODE.get(finding.code)
    return (
        []
        if info is None
        else [f"  fix: {info.fix}", f"  see: {finding_url(__version__, info.see)}"]
    )
