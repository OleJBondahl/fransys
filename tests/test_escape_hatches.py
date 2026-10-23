"""Ratchet of the escape hatches (spec CONSOLIDATE C3): `# noqa` codes and `# ty: ignore` rules.

Counts every code of a `# noqa: A, B` comment and every rule of a `# ty: ignore[rule]` comment
(as `ty-<rule>`) in `packages/*/src`; a bare `# noqa` counts as `noqa-bare`. The total and each
code only fall (`tests/ratchets.toml` `[escape_hatches]`, `[escape_hatches_codes]`).
"""

import io
import re
import tokenize
import tomllib
from collections import Counter

import pytest
from gate_scan import RATCHETS, ROOT, check_stock, ci_gates, stock

_NOQA = re.compile(r"#\s*noqa\b(?::\s*(?P<codes>[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*))?")
_TY = re.compile(r"#\s*ty:\s*ignore(?:\[(?P<rules>[^\]]*)\])?")


def hatches(source: str) -> Counter[str]:
    """Each escape-hatch code in the comments of `source`, counted."""
    found: Counter[str] = Counter()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type != tokenize.COMMENT:
            continue
        if noqa := _NOQA.search(tok.string):
            codes = noqa["codes"]
            found.update(re.split(r"\s*,\s*", codes) if codes else ["noqa-bare"])
        if ty := _TY.search(tok.string):
            rules = [r.strip() for r in (ty["rules"] or "").split(",") if r.strip()]
            found.update(f"ty-{r}" for r in rules or ["bare"])
    return found


def _src_hatches() -> Counter[str]:
    found: Counter[str] = Counter()
    for path in ci_gates.source_files(ROOT):
        found.update(hatches(path.read_text(encoding="utf-8")))
    return found


def test_hatches_counts_every_code_of_a_comment() -> None:
    src = (
        "x = 1  # noqa: PLR0913, S101\n"
        "y = 2  # ty: ignore[invalid-argument-type]\n"
        'z = "# noqa: A1"\n'
        "w = 3  # noqa\n"
    )
    assert hatches(src) == Counter(
        {"PLR0913": 1, "S101": 1, "ty-invalid-argument-type": 1, "noqa-bare": 1}
    )


@pytest.mark.private_input  # a private-gate count (R462)
def test_escape_hatches_stay_at_their_stock() -> None:
    found = _src_hatches()
    table = tomllib.loads(RATCHETS.read_text())["escape_hatches_codes"]
    for code in sorted(found.keys() | table.keys()):
        check_stock(f"escape hatch {code}", found.get(code, 0), table.get(code, 0))
    check_stock("escape_hatches total", sum(found.values()), stock("escape_hatches", "total"))
