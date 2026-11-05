"""Field case: a spare terminal strip with no part of its own, whose terminals disagree on the class code or have none.
The bug: such a strip got no designation and no finding, so fr.write died on a bare SchemaError printing it.
Fixed by model-0134, such a strip is an ERROR naming its key and the cause, so fr.write raises BuildFailedError and writes nothing."""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys.pipeline import BuildFailedError

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
    return [f for f in result.findings if f.severity is Severity.ERROR and any(all_items[s].key == ("spare",) for s in f.subjects if s in all_items)]


@pytest.mark.parametrize("fill", _CASES)
def test_the_strip_gets_an_error_naming_its_kind_not_its_key(fill: Any) -> None:
    result = _built(fill)
    expect_codes(result, "STRIP_WITHOUT_TAG")
    (finding,) = _named_errors(result)
    assert finding.message.startswith(("strip ", "device "))
    assert "spare" not in finding.message


@pytest.mark.parametrize("fill", _CASES)
def test_write_raises_build_errors_not_a_bare_schema_error(fill: Any) -> None:
    built = _built(fill)
    expect_codes(built, "STRIP_WITHOUT_TAG")
    with pytest.raises(BuildFailedError):
        fr.write(built, Path(tempfile.mkdtemp()))
