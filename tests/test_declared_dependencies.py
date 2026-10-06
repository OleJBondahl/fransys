"""Declared-dependency gate: every import a package's `src` makes must be declared in that
package's OWN `pyproject.toml` `[project] dependencies` (spec section 5, root CLAUDE.md
invariant 2).

`test_boundaries.py` checks imports against the allowed-import TABLE, never against each
package's declared dependencies: inside the uv workspace every member is installed, so a
package that imports an undeclared sibling never fails there -- only a consumer installing one
package by itself (e.g. by git subdirectory) sees `ModuleNotFoundError`. This is the check that
was missing, and what caught `fransys` importing `fransys_layout`
(`packages/fransys/src/fransys/pipeline.py:29`) without declaring it in
`packages/fransys/pyproject.toml`.

First-party only. `test_boundaries.THIRD_PARTY` maps each package to the third-party IMPORT
names it may use, not to PyPI/git distribution names (`PIL`/`pillow`, `yaml`/`pyyaml` are the
classic cases where the two differ) -- there is no import-name -> distribution-name table
anywhere in the workspace to check third-party imports against, so this gate does not attempt
it.
"""

import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_boundaries import ALLOWED, FIRST_PARTY, _imported, _source_packages
from test_pins import _REQUIREMENT as _DEPENDENCY
from test_pins import _normalize


def _own_pyproject(package_dir: Path) -> Path:
    """`package_dir` is `packages/<pkg>/src/<import_name>`; its own manifest is two levels up."""
    return package_dir.parent.parent / "pyproject.toml"


def _declared_dependencies(pyproject_path: Path) -> list[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data.get("project", {}).get("dependencies", [])


def undeclared(imports: set[str], dependencies: list[str]) -> set[str]:
    """`imports` not covered by `dependencies` (normalised, extras/markers/specifiers ignored)."""
    declared: set[str] = set()
    for dep in dependencies:
        match = _DEPENDENCY.match(dep.split(";", 1)[0].strip())
        if match:
            declared.add(_normalize(match.group(1)))
    return {name for name in imports if _normalize(name) not in declared}


def _first_party_imports(package_dir: Path) -> set[str]:
    """First-party names `package_dir`'s source imports, own name excluded."""
    found: set[str] = set()
    for path in package_dir.rglob("*.py"):
        found |= _imported(path.read_text(encoding="utf-8"))
    return (found & FIRST_PARTY) - {package_dir.name}


@pytest.mark.parametrize("package_dir", _source_packages(), ids=lambda p: p.name)
def test_first_party_imports_are_declared_dependencies(package_dir: Path):
    imports = _first_party_imports(package_dir)
    dependencies = _declared_dependencies(_own_pyproject(package_dir))
    assert undeclared(imports, dependencies) == set()


def test_every_source_package_was_scanned():
    # Guards against this file's own package discovery silently collecting fewer packages than
    # test_boundaries.py's ALLOWED table expects (e.g. an emptied or narrowed glob).
    assert len(_source_packages()) == len(ALLOWED)


def test_at_least_one_first_party_import_was_found():
    # Guards against a broken scan (e.g. `_imported` returning nothing) passing vacuously.
    total = sum(len(_first_party_imports(p)) for p in _source_packages())
    assert total > 0


def test_the_gate_can_fail():
    imports = {"fransys_layout", "fransys_model"}
    assert undeclared(imports, ["fransys-model"]) == {"fransys_layout"}
    # Underscore/hyphen normalisation: a declared `fransys-layout` covers an imported
    # `fransys_layout`.
    assert undeclared(imports, ["fransys-model", "fransys-layout"]) == set()
