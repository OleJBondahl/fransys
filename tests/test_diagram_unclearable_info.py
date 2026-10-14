"""The two 0.18.6 diagram lints no consumer clears are INFO and never stop a write (layout-0252).

A block diagram that strikes a label or shares a track is a Fransys drawing defect, so
`DIAGRAM_LABEL_STRUCK` and `DIAGRAM_LINES_SHARE_TRACK` are INFO and `fr.write` still writes.
"""

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import fransys as fr  # noqa: E402 -- after the sys.path insert
from test_block_diagram_facade import _built, _system  # noqa: E402 -- ditto

from fransys_layout.lint import diagram  # noqa: E402 -- ditto
from fransys_layout.lint.codes import DIAGRAM_LABEL_STRUCK, DIAGRAM_LINES_SHARE_TRACK  # noqa: E402
from fransys_model.kernel import Severity  # noqa: E402 -- ditto

_CASES = [
    (DIAGRAM_LABEL_STRUCK, "check_label_struck"),
    (DIAGRAM_LINES_SHARE_TRACK, "check_collinear_overlap"),
]


@pytest.mark.parametrize(("code", "check"), _CASES)
def test_the_code_is_info_and_a_build_carrying_it_still_writes(monkeypatch, tmp_path, code, check):
    """Probe: turn `DIAGRAM_LABEL_STRUCK` back to ERROR and this fails."""
    monkeypatch.setattr(diagram, check, lambda _scene: (diagram._error(code, (), "seeded"),))
    result = _built(3, _system())
    seeded = [f for f in fr.check(result) if f.code == code]
    assert seeded
    assert {f.severity for f in seeded} == {Severity.INFO}
    fr.write(result, tmp_path / "out")
    assert any((tmp_path / "out").iterdir())
