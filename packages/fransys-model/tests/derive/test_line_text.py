"""Tests for the harness-line texts: `line_designation` (HL3) and `line_stub_line` (HL1)."""

import pytest
from test_harness_line_ends import _Line

from fransys_model.derive import line_designation, line_stub_line
from fransys_model.kernel import SchemaError


def test_a_line_between_two_ends_prints_its_designation_once() -> None:
    """One plug and one device make two ends: `-WH1` for either branch, no suffix."""
    line = _Line(("P1",))
    model = line.model()
    assert [line_designation(model, line.harness, n) for n in (1, 2)] == ["-WH1", "-WH1"]


def test_a_line_of_three_ends_prints_the_branch_number_on_each() -> None:
    """Two plugs and a device make three ends: `-WH1.n`, n read from the branch."""
    line = _Line(("P2", "P1"))
    model = line.model()
    assert [line_designation(model, line.harness, n) for n in (1, 2, 3)] == [
        "-WH1.1",
        "-WH1.2",
        "-WH1.3",
    ]


def test_a_branch_that_is_not_an_end_is_refused() -> None:
    """Branch 4 of a three-ended line, and branch 0, raise."""
    line = _Line(("P2", "P1"))
    for branch in (0, 4):
        with pytest.raises(SchemaError):
            line_designation(line.model(), line.harness, branch)


def test_a_leaving_line_prints_one_stub_in_the_stub_text_form() -> None:
    """`-W3 → +EXT-M1`, `←` facing north, no cable leaves just the arrow and the far device."""
    assert line_stub_line("-W3", north=False, far="+EXT-M1") == "-W3 → +EXT-M1"
    assert line_stub_line("-W3", north=True, far="+EXT-M1") == "-W3 ← +EXT-M1"
    assert line_stub_line("", north=False, far="+EXT-M1") == "→ +EXT-M1"
