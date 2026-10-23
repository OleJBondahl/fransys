"""Every ERROR or WARNING code's fix is in the message grammar (API-DESIGN AD9, decision 0234).

The grammar is `<valid values>. Write: <corrected call>`; the message holds the cause. A fix is a
`str.format` template whose placeholders come from one closed set, so a raise site can fill it. A
code no consumer call clears says so in the words `No call clears this:` and is never silent.
"""

import re
from string import Formatter

import fransys_el
import fransys_kicad
import fransys_parts
import fransys_pdf
import fransys_render
import pytest
from fransys import _codes

import fransys_layout
from fransys_model import vocab
from fransys_model.kernel import CodeInfo, Severity

FIELDS = frozenset({"subject", "other", "value", "valid", "page"})
WRITE = re.compile(r"(^|\. )Write: \S")
NO_CALL = "No call clears this:"
# API-FINDINGS-FILL: the facade fills `<subject>` and `<other>`; every other `<...>` is a call
# shape the consumer fills. A new name joins this set only with its template.
PLACEHOLDER = re.compile(r"<([^<>]+)>")
CALL_NAMES = frozenset({
    "block", "by", "contract key", "cover", "date", "distinct name", "function", "location",
    "mapping", "mpn", "n", "name", "nested unit", "new", "new revision", "number", "page kind",
    "port", "preset", "revision entry", "same value", "shorter cover file", "shorter notice",
    "shorter text", "symbol", "tag", "target", "text", "thing", "title", "unit",
})  # fmt: skip
FILLED = frozenset({"subject", "other"})

GROUPS: dict[str, tuple[CodeInfo, ...]] = {
    "model": tuple(vocab.FINDING_CODES),
    "parts": tuple(fransys_parts.FINDING_CODES),
    "el": tuple(fransys_el.FINDING_CODES),
    "layout": tuple(fransys_layout.FINDING_CODES),
    "render": tuple(fransys_render.FINDING_CODES),
    "pdf": tuple(fransys_pdf.FINDING_CODES),
    "kicad": tuple(fransys_kicad.FINDING_CODES),
    "facade": tuple(info for info in _codes._OWN),
}
# Every group's templates are in the grammar (API-FINDINGS B to E).
PENDING: frozenset[str] = frozenset()

NEEDS_FIX = [
    pytest.param(info, id=info.code)
    for group, infos in GROUPS.items()
    if group not in PENDING
    for info in infos
    if set(info.severities) & {Severity.ERROR, Severity.WARNING}
]


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name}


def test_the_groups_hold_every_registered_code() -> None:
    held = {info.code for infos in GROUPS.values() for info in infos}
    assert held == set(_codes.BY_CODE)


@pytest.mark.parametrize("info", NEEDS_FIX)
def test_an_error_or_warning_fix_is_in_the_grammar(info: CodeInfo) -> None:
    assert WRITE.search(info.fix) or info.fix.startswith(NO_CALL), info.fix


@pytest.mark.parametrize("info", NEEDS_FIX)
def test_a_fix_uses_only_the_closed_set_of_fields(info: CodeInfo) -> None:
    assert _fields(info.fix) <= FIELDS, info.fix


def test_the_checks_can_fail() -> None:
    bad = CodeInfo(
        code="X", severities=(Severity.ERROR,), stage="s", who="consumer", cause="c",
        fix="Give a name {nope}.", page="p",
    )  # fmt: skip
    assert not WRITE.search(bad.fix)
    assert not _fields(bad.fix) <= FIELDS


def test_the_word_defect_is_in_only_the_two_info_fixes() -> None:
    """A consumer-clearable code never calls itself a Fransys defect (API-FINDINGS G)."""
    named = {
        info.code for infos in GROUPS.values() for info in infos if "defect" in info.fix.lower()
    }
    assert named == set()
    for code in named:
        assert _codes.BY_CODE[code].severities == (Severity.INFO,), code


def _unknown_placeholders(template: str) -> set[str]:
    return set(PLACEHOLDER.findall(template)) - FILLED - CALL_NAMES


@pytest.mark.parametrize("info", [pytest.param(i, id=i.code) for i in _codes.BY_CODE.values()])
def test_a_placeholder_is_subject_other_or_a_call_name(info: CodeInfo) -> None:
    assert not _unknown_placeholders(info.fix), info.fix


def test_an_unknown_placeholder_is_refused() -> None:
    assert _unknown_placeholders("Wire <subjct> to a block.") == {"subjct"}
