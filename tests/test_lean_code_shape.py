"""`scripts/lean_code_shape.py`: `measure_nested_defs`, `measure_module_code_lines`.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. Each test builds its own tiny
`packages/<pkg>/src/<pkg>/mod.py` tree under `tmp_path`, since both measure functions walk
`packages/*/src` off the `root` they are given.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_code_shape", ROOT / "scripts" / "lean_code_shape.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_code_shape.py"
    raise ImportError(msg)
lean_code_shape = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_code_shape
_spec.loader.exec_module(lean_code_shape)

_ceilings_spec = importlib.util.spec_from_file_location(
    "fransys_lean_ceilings", ROOT / "scripts" / "lean_ceilings.py"
)
if _ceilings_spec is None or _ceilings_spec.loader is None:
    msg = "could not load scripts/lean_ceilings.py"
    raise ImportError(msg)
lean_ceilings = importlib.util.module_from_spec(_ceilings_spec)
sys.modules[_ceilings_spec.name] = lean_ceilings
_ceilings_spec.loader.exec_module(lean_ceilings)


def _write_module(tmp_path: Path, body: str) -> Path:
    """Write `body` as `packages/pkg/src/pkg/mod.py` under `tmp_path`; return `tmp_path`."""
    mod = tmp_path / "packages" / "pkg" / "src" / "pkg" / "mod.py"
    mod.parent.mkdir(parents=True)
    mod.write_text(body, encoding="utf-8")
    return tmp_path


_MOD_KEY = "packages/pkg/src/pkg/mod.py"


# --- Check 1: nested defs -------------------------------------------------------------------


def test_nested_def_in_function_is_flagged(tmp_path):
    """A `def` inside a function's immediate body is a violation (`check`, limit 0)."""
    root = _write_module(
        tmp_path,
        "def outer():\n    x = 1\n\n    def inner():\n        return x\n\n    return inner\n",
    )
    measured = lean_code_shape.measure_nested_defs(root)
    assert measured == {f"{_MOD_KEY}::outer": 1}
    violations = lean_ceilings.check(measured, {}, limit=0)
    assert len(violations) == 1
    assert violations[0].site == f"{_MOD_KEY}::outer"


def test_lambda_is_not_flagged(tmp_path):
    """A `lambda` assigned to a local variable is never a nested def."""
    root = _write_module(
        tmp_path,
        "def outer():\n    f = lambda: 1\n    return f\n",
    )
    measured = lean_code_shape.measure_nested_defs(root)
    assert measured == {}


def test_method_with_nested_def_qualname(tmp_path):
    """A method's nested def is keyed `Class.method`, not just the method's bare name."""
    root = _write_module(
        tmp_path,
        (
            "class Foo:\n"
            "    def method(self):\n"
            "        def inner():\n"
            "            return 1\n\n"
            "        return inner\n"
        ),
    )
    measured = lean_code_shape.measure_nested_defs(root)
    assert measured == {f"{_MOD_KEY}::Foo.method": 1}


def test_nested_def_two_levels_deep_charged_to_own_immediate_parent():
    """A def nested two levels deep is charged to its own immediate parent only, never to the
    top-level outer function (no double counting up the chain).
    """
    import ast

    tree = ast.parse(
        "def outer():\n"
        "    def middle():\n"
        "        def inner():\n"
        "            return 1\n\n"
        "        return inner\n\n"
        "    return middle\n"
    )
    walker = lean_code_shape._ScopeWalker()
    walker.visit(tree)
    assert walker.counts == {"outer": 1, "outer.middle": 1}


# --- Check 2: module code lines --------------------------------------------------------------


def _code_lines(n: int) -> str:
    """`n` simple module-level statements, one per line, each a real code line."""
    return "\n".join(f"x{i} = {i}" for i in range(n)) + "\n"


def test_301_code_line_module_fails(tmp_path):
    """A 301-code-line module is over the 300 limit."""
    root = _write_module(tmp_path, _code_lines(301))
    measured = lean_code_shape.measure_module_code_lines(root, limit=300)
    assert measured == {_MOD_KEY: 301}
    violations = lean_ceilings.check(measured, {}, limit=300)
    assert len(violations) == 1


def test_300_code_line_module_passes(tmp_path):
    """A 300-code-line module is exactly at the limit: not a violation (boundary case)."""
    root = _write_module(tmp_path, _code_lines(300))
    measured = lean_code_shape.measure_module_code_lines(root, limit=300)
    assert measured == {}


def test_301_raw_lines_with_only_250_code_lines_passes(tmp_path):
    """301 raw lines but only 250 real code lines (the rest blank or comment-only) is measured
    by code lines, not raw lines, so it stays under the 300 limit.
    """
    extra = ["", "# a comment"] * 25 + [""]  # 51 raw, non-code lines
    blank_and_comment = "\n".join(extra) + "\n"
    body = _code_lines(250) + blank_and_comment
    assert len(body.splitlines()) == 301
    root = _write_module(tmp_path, body)
    measured = lean_code_shape.measure_module_code_lines(root, limit=300)
    assert measured == {}


def test_docstrings_comments_and_blanks_are_not_code_lines():
    """Module, class, function and method docstrings, comments and blanks count as 0."""
    source = (
        '"""Module docstring.\n\nSecond paragraph.\n"""\n\n'
        "# a comment\n"
        "X = 1\n\n\n"
        "class C:\n"
        '    """Class docstring\n    over two lines."""\n\n'
        "    def m(self):\n"
        '        """Method docstring."""\n'
        "        return 1\n\n\n"
        "def f():\n"
        '    """Function\n    docstring\n    here."""\n'
        "    return 2\n"
    )
    # code: X = 1, class C:, def m, return 1, def f, return 2
    assert lean_code_shape.count_code_lines(source) == 6


def test_non_docstring_string_statement_still_counts():
    """A bare string that is not the first statement of its body is code, not a docstring."""
    assert lean_code_shape.count_code_lines('X = 1\n"not a docstring"\n') == 2


def test_module_at_limit_plus_docstring_lines_stays_green(tmp_path):
    """Probe A shape: 300 code lines plus 20 docstring lines is not over the limit."""
    docstring = '"""' + "\n".join(f"doc line {i}" for i in range(20)) + '\n"""\n'
    root = _write_module(tmp_path, docstring + _code_lines(300))
    assert lean_code_shape.measure_module_code_lines(root, limit=300) == {}


def test_module_at_limit_plus_code_lines_fails(tmp_path):
    """Probe B shape: 300 code lines plus 20 more code lines is over the limit."""
    root = _write_module(tmp_path, _code_lines(320))
    assert lean_code_shape.measure_module_code_lines(root, limit=300) == {_MOD_KEY: 320}


# --- LC2 amendment 2026-10-02: a pure re-export module is exempt ------------------------------


def _reexport_source(n: int) -> str:
    """A docstring, `n` imports and the `__all__` naming them: no other statement."""
    names = [f"n{i}" for i in range(n)]
    imports = "".join(f"from pkg.other import {name}\n" for name in names)
    return f'"""Re-exports."""\n\n{imports}\n__all__ = [{", ".join(map(repr, names))}]\n'


def test_derive_init_is_exempt_with_no_ceilings_key():
    """The model's derive `__init__` is a pure re-export module: unmeasured, and no key."""
    rel = "packages/fransys-model/src/fransys_model/derive/__init__.py"
    source = (ROOT / rel).read_text(encoding="utf-8")
    assert lean_code_shape.count_code_lines(source) > 300
    assert lean_code_shape.is_pure_reexport(source)
    assert rel not in lean_code_shape.measure_module_code_lines(ROOT, limit=300)
    assert rel not in (ROOT / "ceilings.toml").read_text(encoding="utf-8")


def test_pure_reexport_over_limit_is_exempt_until_it_gains_a_def(tmp_path):
    """Over 300 code lines it is green; the same module with one def is measured and fails."""
    source = _reexport_source(310)
    root = _write_module(tmp_path, source)
    assert lean_code_shape.measure_module_code_lines(root, limit=300) == {}
    # UNDO: scripts/lean_code_shape.py `is_pure_reexport` returns True for every module
    (root / _MOD_KEY).write_text(source + "\n\ndef f():\n    return 1\n", encoding="utf-8")
    measured = lean_code_shape.measure_module_code_lines(root, limit=300)
    assert list(measured) == [_MOD_KEY]
    assert len(lean_ceilings.check(measured, {}, limit=300)) == 1
