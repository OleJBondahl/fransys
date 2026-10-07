"""`grid_path` returns the path recorded from today's suite, and the oracle's, call by call.

The tracked sample (`data/grid_path_sample.json`, built by `claude-tools/grid_path_sample.py`)
always runs. The full recording (`.fransys/grid-calls/*.pkl`, made by
`claude-tools/grid_path_record.py`) is local and gitignored. It replays only when present, takes
about 100 s, and checks the recorded paths alone: the oracle's agreement is checked on the sample
and by the property test.
"""

import json
import pickle
from pathlib import Path

import pytest
from grid_path_calls import decode
from grid_path_oracle import oracle_path

from fransys_layout.stages.grid_path import grid_path

_SAMPLE = Path(__file__).parent / "data" / "grid_path_sample.json"
_RECORDED = sorted(Path(__file__).parents[4].glob(".fransys/grid-calls/*.pkl"))


def _agree(start, goal, field, path) -> None:
    assert grid_path(start, goal, field) == path
    assert oracle_path(start, goal, field) == path


def test_the_sample_replays() -> None:
    calls = [decode(raw) for raw in json.loads(_SAMPLE.read_text(encoding="utf-8"))]
    assert len(calls) >= 150
    assert sum(1 for _, _, field, _ in calls if field.free) >= 40
    assert any(path is None for *_, path in calls)
    for call in calls:
        _agree(*call)


@pytest.mark.skipif(not _RECORDED, reason="no local recording in .fransys/grid-calls/")
def test_the_full_recording_replays() -> None:
    for file in _RECORDED:
        for start, goal, field, path in pickle.loads(file.read_bytes()):  # noqa: S301  (our own gitignored recording)
            assert grid_path(start, goal, field) == path
