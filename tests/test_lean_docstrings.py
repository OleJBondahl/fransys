"""`scripts/lean_docstrings.py`: surface-docstring presence/length, non-surface shape.

Loaded by file path, as the script is no package module. Check 2's tests build tiny trees under
`tmp_path`; check 1's pass their own `entries`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from gate_scan import load_script

ROOT = Path(__file__).resolve().parents[1]


lean_surface = load_script("fransys_lean_surface", "lean_surface.py")
lean_docstrings = load_script("fransys_lean_docstrings", "lean_docstrings.py")
lean_ceilings = load_script("fransys_lean_ceilings", "lean_ceilings.py")


def _write_module(tmp_path: Path, body: str, rel: str = "packages/pkg/src/pkg/mod.py") -> Path:
    """Write `body` as `rel` under `tmp_path`; return `tmp_path`."""
    mod = tmp_path / rel
    mod.parent.mkdir(parents=True)
    mod.write_text(body, encoding="utf-8")
    return tmp_path


_MOD_KEY = "packages/pkg/src/pkg/mod.py"
_SIX = 'def f():\n    """One.\n\n    Two.\n    Three.\n    Four.\n    """\n    return 1\n'


# --- Check 2: non-surface docstring length (ceiling-bound) ---------------------------------


@pytest.mark.parametrize(
    ("rel", "body", "site", "lines"),
    [
        *((rel, _SIX, "f", 6) for rel in (_MOD_KEY, "tests/test_mod.py", "packages/pkg/tests/test_mod.py", "tools/tests/test_mod.py")),
        ("tests/field_cases/test_mod.py", '"""One.\n\nTwo.\nThree."""\n', "<module>", 4),
    ],
)
def test_docstring_over_its_cap_is_measured_in_source_and_test_trees(tmp_path, rel, body, site, lines):
    """A 6-line docstring (src, any test tree) or a 4-line field-case module docstring (cap 3) is
    measured over its cap, and `lean_ceilings.check` fails it as unlisted.
    """
    measured = lean_docstrings.measure_docstring_lines(_write_module(tmp_path, body, rel), frozenset())
    assert [(v.site, v.measured) for v in lean_ceilings.check(measured, {}, limit=5)] == [(f"{rel}::{site}", lines)]


def test_returns_section_in_short_non_surface_docstring_is_flagged(tmp_path):
    """A `Returns:` line in a <=3-line non-surface docstring is a banned-section site."""
    root = _write_module(
        tmp_path,
        'def g():\n    """Summary.\n    Returns:\n    """\n    return 1\n',
    )
    banned = lean_docstrings.banned_section_sites(root, frozenset())
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
    assert violations == (lean_docstrings.SurfaceDocstringViolation("fake_surface.py::Foo", "missing"),)


def test_surface_docstring_over_15_lines_fails(tmp_path):
    """A surface name with a real docstring over `limit` lines fails, distinctly from `missing`."""
    fake = tmp_path / "fake_surface.py"
    lines = "\n".join(f"    Line {n}." for n in range(1, 15))
    fake.write_text(f'def f():\n    """Summary.\n\n{lines}\n    """\n    return 1\n', encoding="utf-8")
    entry = lean_surface.SurfaceName(module="fake", name="f", defining_file=fake, qualname="f")
    violations = lean_docstrings.check_surface_docstrings(entries=(entry,), root=tmp_path)
    assert len(violations) == 1
    assert violations[0].site == "fake_surface.py::f"
    assert "lines (max 15)" in violations[0].reason


def test_surface_docstring_within_15_lines_with_returns_section_passes():
    """`fransys.parts` (the real, shipped guide shape: Args, Returns, 11 lines) is on
    the real surface and is not a violation -- the length cap and the Google-section allowance
    both hold for it.
    """
    violations = lean_docstrings.check_surface_docstrings()
    site = "packages/fransys/src/fransys/pipeline.py::parts"
    assert site not in {violation.site for violation in violations}


# --- Check 1 reaches the public methods a surface class inherits (R665) --------------------


def _surface_with_mixin(tmp_path: Path, helper_doc_lines: int, method_doc_lines: int) -> tuple[Path, object]:
    """`Top(Mixin)` in `top.py`, `Mixin` imported from `mixin.py`; return root and the `Top` entry."""
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True)

    def doc(n: int) -> str:
        return '        """Summary.\n\n' + "".join(f"        Line {i}.\n" for i in range(n - 3)) + '        """\n'

    (pkg / "mixin.py").write_text(
        f"class Mixin:\n    def method(self):\n{doc(method_doc_lines)}        return 1\n\n"
        f"    def _helper(self):\n{doc(helper_doc_lines)}        return 1\n",
        encoding="utf-8",
    )
    top = pkg / "top.py"
    top.write_text('from .mixin import Mixin\n\n\nclass Top(Mixin):\n    """A surface class."""\n', encoding="utf-8")
    return tmp_path, lean_surface.SurfaceName(module="pkg.top", name="Top", defining_file=top, qualname="Top")


def test_an_inherited_public_method_is_checked_against_the_surface_limit_not_the_plain_one(tmp_path):
    """A 9-line docstring on a mixin's public method passes (15 allowed); a 17-line one fails."""
    root, entry = _surface_with_mixin(tmp_path, 3, 9)
    assert lean_docstrings.check_surface_docstrings(entries=(entry,), root=root) == ()
    assert "pkg/mixin.py::Mixin.method" in lean_docstrings.surface_site_keys(entries=(entry,), root=root)
    root, entry = _surface_with_mixin(tmp_path / "long", 3, 17)
    found = lean_docstrings.check_surface_docstrings(entries=(entry,), root=root)
    assert [v.site for v in found] == ["pkg/mixin.py::Mixin.method"]


def test_an_inherited_private_helper_stays_a_plain_site(tmp_path):
    """A 6-line `_helper` is not surface: it is measured against the 5-line limit."""
    root, entry = _surface_with_mixin(tmp_path, 6, 5)
    assert "pkg/mixin.py::Mixin._helper" not in lean_docstrings.surface_site_keys(entries=(entry,), root=root)
