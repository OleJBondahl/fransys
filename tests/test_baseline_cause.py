"""`BASELINE_DIFFERS` names the child whose release moved (WORKFLOW-BLOCKS W8, acceptance 7)."""

import sys
from pathlib import Path

import fransys as fr
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_cabinet


@pytest.fixture(scope="module")
def released(tmp_path_factory):
    """The cabinet with its board at 1.1, both released."""
    into = tmp_path_factory.mktemp("cause")
    result, _scope = build_cabinet()
    for name in ("wb-board", "wb-cabinet"):
        fr.release(result, into, unit=name)
    return into


def _messages(result, into):
    return [f.message for f in fr.verify(result, into) if f.code == "BASELINE_DIFFERS"]


def test_a_moved_child_is_named_right_after_units_and_before_later_sections(released):
    result, _scope = build_cabinet(board_revision=3, extra_wire=True)
    expected = (
        "wb-cabinet 1.1 differs from its released baseline in: "
        "items, units (wb-board 1.1 → 1.3), conductors"
    )
    assert _messages(result, released) == [expected]


def test_a_removed_child_is_named(released):
    result, _scope = build_cabinet(with_board=False)
    (message,) = _messages(result, released)
    assert "units (wb-board removed)" in message


def test_an_added_child_is_named(tmp_path):
    bare, _ = build_cabinet(with_board=False)
    fr.release(bare, tmp_path, unit="wb-cabinet")
    result, _scope = build_cabinet()
    (message,) = _messages(result, tmp_path)
    assert "units (wb-board added)" in message


def test_a_container_whose_units_did_not_change_keeps_todays_text(released):
    result, _scope = build_cabinet(extra_wire=True)
    (message,) = _messages(result, released)
    assert message == ("wb-cabinet 1.1 differs from its released baseline in: items, conductors")
