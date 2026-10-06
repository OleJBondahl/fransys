"""Field case: a floating terminal strip that cannot be designated is an ERROR, not a crash.

The engineering shape: a cabinet adds a spare terminal strip with `terminal_strip(None, part,
name=)`. The strip has no part of its own and takes its class code from its terminals' part.

The bug: a strip with no terminal, or whose terminals disagree on the class code, got no
designation and no finding (only the INFO `ITEM_WITHOUT_PART`). The build passed, and `fr.write`
died on a bare `SchemaError` ("the item has no designation") when it first printed the strip.

The rule: such a strip is an ERROR finding that names the strip key and says why (no terminals,
or the codes that disagree); `fr.write` raises `BuildErrors` and writes nothing.

The decision that fixes it: model-0134 (numbering), FLOATING-STRIP-ERROR.
"""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from fransys.pipeline import BuildErrors

from fransys_model.kernel import Severity
from fransys_model.vocab.tables import items


def _empty(d: fr.Design) -> None:
    d.terminal_strip(None, "DEMO-TB-2.5", name="spare")


def _disagreeing(d: fr.Design) -> None:
    strip = d.terminal_strip(None, "DEMO-CONN-2P", name="spare", pe="DEMO-TB-PE-2.5")
    strip.run("PE", 1)
    strip.run("L", 1)


_CASES = [
    pytest.param(_empty, id="no_terminals"),
    pytest.param(_disagreeing, id="terminals_disagree"),
]


def _built(fill: Any) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    fill(d)
    return fr.build(d)


def _named_errors(result: fr.BuildResult) -> list[fr.Finding]:
    all_items = items(result.model)
    return [
        f
        for f in result.findings
        if f.severity is Severity.ERROR
        and any(all_items[s].key == ("spare",) for s in f.subjects if s in all_items)
    ]


@pytest.mark.parametrize("fill", _CASES)
def test_the_strip_gets_an_error_naming_its_key(fill: Any) -> None:
    (finding,) = _named_errors(_built(fill))
    assert "spare" in finding.message


@pytest.mark.parametrize("fill", _CASES)
def test_write_raises_build_errors_not_a_bare_schema_error(fill: Any) -> None:
    with pytest.raises(BuildErrors):
        fr.write(_built(fill), Path(tempfile.mkdtemp()))
