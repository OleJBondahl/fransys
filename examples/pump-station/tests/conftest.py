"""Shared "rebuild fresh" fixtures for the checks in spec E9 (STEP 4).

`build.py` is a script, not a package: it is loaded by path with
`importlib.util`, and `fr.build` and the three `fr.write` calls are made here (the script
itself only does that under `if __name__ == "__main__":`). Each `load_build_module()` call
re-execs the module fresh, so a test that Edits `build.py` and calls the `rebuild_fresh` fixture
again always sees the edited version, never a cached one.

Everything cross-module is exposed as a fixture, not as a plain import between test files:
this project's `--import-mode=importlib` pytest setting does not put `tests/` on `sys.path`,
so `from some_test_helper import x` between sibling test modules is not reliable, while
fixture injection always is.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import fransys as fr
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = REPO_ROOT / "build.py"
sys.path.insert(0, str(BUILD_SCRIPT.parent))  # the script imports its typed parts module


def _load_build_module() -> ModuleType:
    """Exec `build.py` fresh and return the loaded module."""
    spec = importlib.util.spec_from_file_location("pump_station_build", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rebuild(tmp_path: Path) -> tuple[fr.BuildResult, Path, Path]:
    """Load `build.py` fresh, build and write its three folders into `tmp_path`.

    Returns the `BuildResult`, the fresh `out_dir` (the root holding `cabinet/`, `board/` and
    `all/`), and the fresh `intermediates` dir (written with the `all/` write only).
    """
    module = _load_build_module()
    result = fr.build(module.d, *module.documents)
    out_dir = tmp_path / "out"
    intermediates = tmp_path / "intermediates"
    fr.write(result, out_dir=out_dir / "cabinet", unit="pump-cabinet")
    fr.write(result, out_dir=out_dir / "board", unit="relay-interface-board")
    fr.write(result, out_dir=out_dir / "all", intermediates=intermediates)
    return result, out_dir, intermediates


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Path, Path]:
    """One rebuild per test module, shared by every read-only assertion test in it.

    Module-scoped: since `build.py` is re-exec'd fresh on every call to
    `_rebuild`, a whole new `pytest` run (as the can-fail probes in the STEP 4 report use,
    run manually after an `Edit`-based mutation) always picks up the current file on disk --
    no test in this suite needs its own function-scoped rebuild.
    """
    tmp_path = tmp_path_factory.mktemp("build")
    return _rebuild(tmp_path)
