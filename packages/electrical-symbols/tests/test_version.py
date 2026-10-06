"""`LIBRARY_VERSION` is the package version, and `_version.py` is what `scripts/build.py` writes.

The stale-constant gate: bump `version` in `pyproject.toml` without running the build script
and this file fails, and so does `just ci`.
"""

import importlib.util
from pathlib import Path

import graphical_symbols

import electrical_symbols

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "electrical_symbols_build", ROOT / "scripts" / "build.py"
)
assert _spec is not None
assert _spec.loader is not None
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
GENERATED = (ROOT / "src" / "electrical_symbols" / "_version.py").read_text(encoding="utf-8")


def test_the_constant_is_the_package_version():
    assert build.project_version(PYPROJECT) == electrical_symbols.LIBRARY_VERSION


def test_the_generated_module_is_what_the_build_writes():
    assert build.version_module(build.project_version(PYPROJECT)) == GENERATED


def test_the_constant_is_public():
    assert "LIBRARY_VERSION" in electrical_symbols.__all__


def test_the_written_module_defines_the_constant():
    namespace: dict[str, str] = {}
    exec(build.version_module("1.2.3"), namespace)  # noqa: S102 (the module the build writes)
    assert namespace["LIBRARY_VERSION"] == "1.2.3"


def test_another_version_in_pyproject_makes_the_module_stale():
    """The gate can fail: a bumped version gives text unlike what is on disk."""
    bumped = build.project_version('[project]\nversion = "9.9.9"\n')
    assert bumped != electrical_symbols.LIBRARY_VERSION
    assert build.version_module(bumped) != GENERATED


def test_library_version_joins_both_packages_versions():
    """`library_version()` is the one home for the string `fransys_layout` used to build (D3)."""
    assert electrical_symbols.library_version() == (
        f"electrical-symbols {electrical_symbols.LIBRARY_VERSION} "
        f"/ graphical-symbols {graphical_symbols.LIBRARY_VERSION}"
    )


def test_library_version_is_public():
    assert "library_version" in electrical_symbols.__all__


def test_library_version_differs_when_either_package_version_does():
    """The gate can fail: joining a different version gives a different string."""
    assert electrical_symbols.library_version() != (
        f"electrical-symbols 9.9.9 / graphical-symbols {graphical_symbols.LIBRARY_VERSION}"
    )
    assert electrical_symbols.library_version() != (
        f"electrical-symbols {electrical_symbols.LIBRARY_VERSION} / graphical-symbols 9.9.9"
    )
