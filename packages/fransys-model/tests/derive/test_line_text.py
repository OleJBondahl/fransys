"""Tests for the harness-line texts: `line_designation` and `line_stub_line`."""

from fransys_model.derive import line_stub_line


def test_a_far_device_prints_the_place_it_is_drawn_at() -> None:
    """The place follows its device, in the position form."""
    far = [("+EXT-M1", "p2:4A")]
    assert line_stub_line("-W3", north=False, far=far) == "-W3 → +EXT-M1 p2:4A"


def test_every_far_device_is_listed_with_its_own_place() -> None:
    """Two far devices print both, `, ` between; one without a place prints bare."""
    far = [("-Q1-J1", "p1:2C"), ("-Q2-J1", "p1:5C")]
    assert line_stub_line("-W1", north=True, far=far) == "-W1 ← -Q1-J1 p1:2C, -Q2-J1 p1:5C"
    mixed = [("-Q1-J1", "p1:2C"), ("-Q2-J1", "")]
    assert line_stub_line("-W1", north=True, far=mixed) == "-W1 ← -Q1-J1 p1:2C, -Q2-J1"


def test_far_devices_without_any_place_keep_today_s_single_device_text() -> None:
    """Nothing drawn in this drawing set names the first device alone, as before."""
    far = [("-Q1-J1", ""), ("-Q2-J1", "")]
    assert line_stub_line("-W1", north=False, far=far) == "-W1 → -Q1-J1"
