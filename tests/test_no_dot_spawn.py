"""CT1 accept: no subprocess (`dot` or otherwise) is spawned building a full document build.

`packages/fransys-wireviz` is archived; nothing left in this workspace's own source calls
`subprocess` while building a document (confirmed: `_tool_versions`'s own `dot -V` probe is
gone too, decision 0055). Proven at the build path itself, not by grep: patches
`subprocess.Popen.__init__` -- the one primitive `run`/`call`/`check_output` all delegate to --
to record every attempted spawn and refuse to start one, so a probe that reintroduces a `dot`
call fails this test with no real Graphviz install needed.
"""

import subprocess
import sys
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design
from test_write_unit_worked_example import _unit_id


class SpawnAttemptedError(Exception):
    """Raised by the patched `Popen.__init__` the moment anything tries to spawn a process."""


def _no_spawn_init(_self, args, *_a, **_kw):
    message = f"a subprocess was spawned: {args!r}"
    raise SpawnAttemptedError(message)


def test_building_the_examples_system_and_unit_documents_spawns_no_subprocess(
    monkeypatch, tmp_path
):
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    draft = design.draft()
    system_cover = tmp_path / "system-cover.md"
    system_cover.write_text("# System\n", encoding="utf-8")
    unit_cover = tmp_path / "unit-cover.md"
    unit_cover.write_text("# Unit\n", encoding="utf-8")
    probe_model = fr.build(
        parts, draft, fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover)
    ).model
    pump1_cabinet = _unit_id(probe_model, name="demo-pump-cabinet", prefix="pump1")

    system_doc = fr.document(fr.DocumentPreset.SYSTEM, None, cover=system_cover)
    unit_doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, pump1_cabinet, cover=unit_cover)

    monkeypatch.setattr(subprocess.Popen, "__init__", _no_spawn_init)

    result = fr.build(parts, draft, system_doc, unit_doc)
    fr.check(result)
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")
    assert written, "sanity: a real build actually happened, not a vacuous pass"


def test_a_reintroduced_dot_call_fails_the_test_above(monkeypatch):
    """Can-fail twin, run inline (not through `just probe`): the same guard, exercised against
    a fake `dot` call planted right where the count test above would otherwise see none, with
    no real Graphviz install needed (the patched `Popen.__init__` never actually spawns).
    """
    monkeypatch.setattr(subprocess.Popen, "__init__", _no_spawn_init)
    with pytest.raises(SpawnAttemptedError):
        subprocess.run(["dot", "-V"], capture_output=True, check=False)  # noqa: S607
