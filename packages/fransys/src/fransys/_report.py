"""`fr.report`: one readable text of a build's findings (BUILD-MESSAGES M10, decision 0192)."""

from collections import Counter

from fransys_model.kernel import Finding, Severity

from ._finding_text import fix_lines
from .pipeline import BuildResult, check

_SUBJECT = "  subject: "
_NAMES = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def report(result: BuildResult) -> str:
    """Output: one text of `fr.check(result)`.

    It holds a summary line, each ERROR and WARNING, then the notes.

    Each ERROR and WARNING prints its message, then an `at:` line per subject, its fix and its
    guide anchor from the code's registry entry. INFO notes print counted per code on one line.
    The text only reads the findings and their `CodeInfo`; it adds no rule of its own.

    Does not write files, raise on an ERROR, or drop a finding.
    """
    findings = check(result)
    counts = Counter(f.severity for f in findings)
    lines = [_summary(counts)]
    for finding in findings:
        if finding.severity is not Severity.INFO:
            lines.extend(_entry(finding))
    notes = Counter(f.code for f in findings if f.severity is Severity.INFO)
    if notes:
        ranked = sorted(notes.items(), key=lambda pair: (-pair[1], pair[0]))
        lines.append("notes: " + ", ".join(f"{code} {n}" for code, n in ranked))
    return "\n".join(lines) + "\n"


def _summary(counts: Counter[Severity]) -> str:
    parts = (_plural(counts[severity], name) for severity, name in _NAMES.items())
    return "build: " + ", ".join(parts)


def _plural(count: int, name: str) -> str:
    return f"{count} {name}" if count == 1 else f"{count} {name}s"


def _entry(finding: Finding) -> list[str]:
    lines = finding.message.splitlines()
    head = [line for line in lines if not line.startswith(_SUBJECT)]
    at = [f"  at: {line.removeprefix(_SUBJECT)}" for line in lines if line.startswith(_SUBJECT)]
    return [*head, *at, *fix_lines(finding)]
