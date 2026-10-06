"""`scripts/lean_docstrings.py`: surface-docstring presence/length, non-surface shape.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. Check 2's tests build their own tiny
`packages/<pkg>/src/<pkg>/mod.py` tree under `tmp_path` (`measure_docstring_lines`/
`banned_section_sites` walk `packages/*/src` off the `root` they are given), the same pattern
`test_lean_code_shape.py` uses. Check 1's tests pass their own `entries` (a hand-built
`lean_surface.SurfaceName` pointing at a `tmp_path` file) instead of the real workspace, since
`check_surface_docstrings` never imports a name to check its docstring -- only `ast`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        msg = f"could not load scripts/{filename}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


lean_surface = _load("fransys_lean_surface", "lean_surface.py")
lean_docstrings = _load("fransys_lean_docstrings", "lean_docstrings.py")
lean_ceilings = _load("fransys_lean_ceilings", "lean_ceilings.py")


def _write_module(tmp_path: Path, body: str) -> Path:
    """Write `body` as `packages/pkg/src/pkg/mod.py` under `tmp_path`; return `tmp_path`."""
    mod = tmp_path / "packages" / "pkg" / "src" / "pkg" / "mod.py"
    mod.parent.mkdir(parents=True)
    mod.write_text(body, encoding="utf-8")
    return tmp_path


_MOD_KEY = "packages/pkg/src/pkg/mod.py"


# --- Check 2: non-surface docstring length (ceiling-bound) ---------------------------------


def test_six_line_non_surface_docstring_is_measured_over_the_cap(tmp_path):
    """A 6-line docstring outside the surface is measured over `DEFAULT_DOCSTRING_LINES_LIMIT`
    (5), and `lean_ceilings.check` fails it as unlisted.
    """
    root = _write_module(
        tmp_path,
        'def f():\n    """One.\n\n    Two.\n    Three.\n    Four.\n    """\n    return 1\n',
    )
    surface: frozenset[str] = frozenset()
    measured = lean_docstrings.measure_docstring_lines(root, surface)
    assert measured == {f"{_MOD_KEY}::f": 6}
    violations = lean_ceilings.check(measured, {}, limit=5)
    assert len(violations) == 1
    assert violations[0].site == f"{_MOD_KEY}::f"


def test_returns_section_in_short_non_surface_docstring_is_flagged(tmp_path):
    """A `Returns:` line in a <=3-line non-surface docstring is a banned-section site."""
    root = _write_module(
        tmp_path,
        'def g():\n    """Summary.\n    Returns:\n    """\n    return 1\n',
    )
    surface: frozenset[str] = frozenset()
    banned = lean_docstrings.banned_section_sites(root, surface)
    assert banned == (f"{_MOD_KEY}::g",)


def test_surface_name_with_no_docstring_fails(tmp_path):
    """A surface name with literally no docstring fails, even though a plain `dataclasses.
    dataclass` fixture would have a real (auto-generated) `obj.__doc__` -- `check_surface_
    docstrings` never looks at it, only at the `ast`.
    """
    fake = tmp_path / "fake_surface.py"
    fake.write_text(
        "import dataclasses\n\n\n@dataclasses.dataclass(frozen=True)\nclass Foo:\n    x: int\n",
        encoding="utf-8",
    )
    entry = lean_surface.SurfaceName(module="fake", name="Foo", defining_file=fake, qualname="Foo")
    violations = lean_docstrings.check_surface_docstrings(entries=(entry,), root=tmp_path)
    assert violations == (
        lean_docstrings.SurfaceDocstringViolation("fake_surface.py::Foo", "missing"),
    )


def test_surface_docstring_over_15_lines_fails(tmp_path):
    """A surface name with a real docstring over `limit` lines fails, distinctly from `missing`."""
    fake = tmp_path / "fake_surface.py"
    lines = "\n".join(f"    Line {n}." for n in range(1, 15))
    fake.write_text(
        f'def f():\n    """Summary.\n\n{lines}\n    """\n    return 1\n', encoding="utf-8"
    )
    entry = lean_surface.SurfaceName(module="fake", name="f", defining_file=fake, qualname="f")
    violations = lean_docstrings.check_surface_docstrings(entries=(entry,), root=tmp_path)
    assert len(violations) == 1
    assert violations[0].site == "fake_surface.py::f"
    assert "lines (max 15)" in violations[0].reason


def test_surface_docstring_within_15_lines_with_returns_section_passes():
    """`fransys.parts` (the real, shipped GUIDE/CG5 shape: Args, Returns, 11 lines) is on
    the real surface and is not a violation -- the length cap and the Google-section allowance
    both hold for it.
    """
    violations = lean_docstrings.check_surface_docstrings()
    site = "packages/fransys/src/fransys/pipeline.py::parts"
    assert site not in {violation.site for violation in violations}
