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
    one = [("+EXT-M1", "")]
    assert line_stub_line("-W3", north=False, far=one) == "-W3 → +EXT-M1"
    assert line_stub_line("-W3", north=True, far=one) == "-W3 ← +EXT-M1"
    assert line_stub_line("", north=False, far=one) == "→ +EXT-M1"


def test_a_far_device_prints_the_place_it_is_drawn_at() -> None:
    """STUB-POSITIONS P1: the place follows its device, in the position form."""
    far = [("+EXT-M1", "p2:4A")]
    assert line_stub_line("-W3", north=False, far=far) == "-W3 → +EXT-M1 p2:4A"


def test_every_far_device_is_listed_with_its_own_place() -> None:
    """R6: two far devices print both, `, ` between; one without a place prints bare."""
    far = [("-Q1-J1", "p1:2C"), ("-Q2-J1", "p1:5C")]
    assert line_stub_line("-W1", north=True, far=far) == "-W1 ← -Q1-J1 p1:2C, -Q2-J1 p1:5C"
    mixed = [("-Q1-J1", "p1:2C"), ("-Q2-J1", "")]
    assert line_stub_line("-W1", north=True, far=mixed) == "-W1 ← -Q1-J1 p1:2C, -Q2-J1"


def test_far_devices_without_any_place_keep_today_s_single_device_text() -> None:
    """P2: nothing drawn in this drawing set names the first device alone, as before."""
    far = [("-Q1-J1", ""), ("-Q2-J1", "")]
    assert line_stub_line("-W1", north=False, far=far) == "-W1 → -Q1-J1"
