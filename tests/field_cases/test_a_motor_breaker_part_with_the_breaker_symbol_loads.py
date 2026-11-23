"""Field case: a motor breaker protection part names the circuit-breaker symbol, the one the symbol table defaults it to.
The bug (KI-1331, closed): parts refused it with SYMBOL_TYPE_MISMATCH while el defaulted to it; `derive.protection_symbols` is now the one table."""

from pathlib import Path

import fransys as fr
import fransys_parts
from _model_build_cover import cabinet_document, error_messages


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", "breaker_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Rail", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-11-21", text="First issue", created="XX")
    q1 = d.device("Q1", "DEMO-MPCB-1P")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    d.series(x1[1].inner, q1.element["1"], wire=("BN", 1.5))
    d.series(q1.element["2"], x1[2].inner, wire=("BK", 1.5))
    return fr.build(d, cabinet_document(cab))


def test_a_motor_breaker_with_the_breaker_symbol_builds_with_no_error() -> None:
    lib = Path(__file__).parent / "data" / "breaker_parts"
    assert [f.code for f in fransys_parts.lint(lib) if f.severity == fr.Severity.ERROR] == []
    assert error_messages(_build()) == []
