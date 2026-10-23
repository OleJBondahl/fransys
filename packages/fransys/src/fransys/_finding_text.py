"""The text of a finding: its subjects printed as names, and its one `CODE (severity):` head."""

from typing import Any

from fransys_model.derive.docs_site import finding_url
from fransys_model.derive.numbering_pins import subject_text
from fransys_model.kernel import (
    DescribedFinding,
    Finding,
    Id,
    Model,
    SchemaError,
    describe,
    describe_parts,
)

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


def filled_fix(finding: Finding, model: Model) -> str:
    """The finding's fix with `<subject>` and `<other>` set to its first and second subject.

    A subject prints as its `at:` line does. Any other `<...>` stays; a missing subject raises.
    """
    shown = described_parts(finding, model).subjects
    fix = finding.fix or ""
    for placeholder, index in (("<subject>", 0), ("<other>", 1)):
        if placeholder not in fix:
            continue
        if index >= len(shown):
            msg = (
                f"{finding.code}: the fix holds {placeholder} but the finding has no subject "
                f"there; name the thing and the fix: {finding.fix!r}"
            )
            raise SchemaError(msg, kind="Finding")
        fix = fix.replace(placeholder, shown[index])
    return fix


def fix_lines(finding: Finding, model: Model) -> list[str]:
    """The finding's own fix and the URL of its code's row on this release's findings page.

    BUILD-MESSAGES M2, DOCS-FOR-AGENTS D6, API-FINDINGS: the fix is the row's `fix`, never the
    registry's text. A code with no registry entry gives no URL; an INFO row without a fix, none.
    """
    info = BY_CODE.get(finding.code)
    fix = [f"  fix: {filled_fix(finding, model)}"] if finding.fix else []
    url = [] if info is None else [f"  see: {finding_url(__version__, info.see)}"]
    return [*fix, *url]
