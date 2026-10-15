"""`CodeInfo`: one finding code's home (BUILD-MESSAGES M1, decision model-0223)."""

import dataclasses

import pytest

from fransys_kernel import WHO_ACTS, CodeInfo, SchemaError, Severity

_GOOD = CodeInfo(
    code="LONE_CELL",
    severities=(Severity.WARNING,),
    stage="render",
    who="consumer",
    cause="A symbol has no drawn conductor.",
    fix="Wire the port.",
    page="findings-render",
)


def test_a_code_info_names_its_guide_anchor():
    assert _GOOD.see == "findings-render#lone_cell"


def test_who_acts_has_the_four_classes():
    assert WHO_ACTS == ("consumer", "part author", "Fransys", "note")


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"code": "lone_cell"}, "UPPER_SNAKE"),
        ({"who": "user"}, "who 'user'"),
        ({"severities": ()}, "no severity"),
        ({"fix": ""}, "non-empty"),
        ({"page": ""}, "non-empty"),
    ],
)
def test_a_malformed_code_info_is_refused(change, problem):
    with pytest.raises(SchemaError, match=problem):
        dataclasses.replace(_GOOD, **change)


def test_a_code_info_is_frozen():
    info = _GOOD
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.fix = "x"  # ty: ignore[invalid-assignment] -- the frozen refusal is what is tested
