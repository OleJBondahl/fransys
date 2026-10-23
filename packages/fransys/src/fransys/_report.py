"""`fr.report`: one readable text of a build's findings (BUILD-MESSAGES M10, decision 0192)."""

from collections import Counter

from fransys_model.kernel import DescribedFinding, Finding, Model, Severity

from ._finding_text import described, described_parts, fix_lines
from .pipeline import BuildResult, _raw_findings, _resolved, _result_svgs

_NAMES = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def report(result: BuildResult) -> str:
    """Output: one text of `fr.check(result)`.

    It holds a summary line, each ERROR and WARNING, then the notes.

    Each ERROR and WARNING prints its message, then an `at:` line per subject, its own `fix` and
    the URL of its code's findings row. INFO notes print counted per code on one line.
    The text only reads the findings and their `CodeInfo`; it adds no rule of its own.

    Does not write files, raise on an ERROR, or drop a finding.
    """
    entries = _described(result)
    findings = [finding for finding, _ in entries]
    counts = Counter(f.severity for f in findings)
    lines = [_summary(counts)]
    for finding, parts in entries:
        if finding.severity is not Severity.INFO:
            lines.extend(_entry(finding, parts, result.model))
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


def _described(result: BuildResult) -> list[tuple[Finding, DescribedFinding]]:
    """`check(result)`, each finding with its text kept as head and subjects (model-0273)."""
    model = result.model
    raw = _raw_findings(result, _result_svgs(result))
    parts = {(f.code, f.subjects, described(f, model)): described_parts(f, model) for f in raw}
    return [(f, parts[f.code, f.subjects, f.message]) for f in _resolved(raw, model)]


def _entry(finding: Finding, parts: DescribedFinding, model: Model) -> list[str]:
    at = [f"  at: {subject}" for subject in parts.subjects]
    return [*parts.head.splitlines(), *at, *fix_lines(finding, model)]
