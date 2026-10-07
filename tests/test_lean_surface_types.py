"""`scripts/lean_surface_types.py`: `measure_surface_types`, `measure_record_field_types`.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. Every test mocks a small surface by
monkeypatching `lean_surface.resolve_surface_names` (the module attribute the loaded
`lean_surface_types` module itself calls) to return a hand-built `SurfaceName` pointing at a
`tmp_path` file, and `lean_surface.ROOT` to `tmp_path` so the real workspace root's own
signatures never leak into a fixture's expected count.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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
lean_surface_types = _load("fransys_lean_surface_types", "lean_surface_types.py")


def _write(tmp_path: Path, name: str, body: str) -> Path:
    """Write `body` as `<tmp_path>/<name>`; return its path."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _mock_surface(monkeypatch, tmp_path: Path, entries: tuple) -> None:
    """Patch `lean_surface` so `resolve_surface_names()` returns `entries` under `tmp_path`."""
    monkeypatch.setattr(lean_surface, "ROOT", tmp_path)
    monkeypatch.setattr(lean_surface, "resolve_surface_names", lambda _modules=None: entries)


def _entry(path: Path, name: str, qualname: str | None = None) -> object:
    return lean_surface.SurfaceName(
        module="fake", name=name, defining_file=path, qualname=qualname or name
    )


# --- Acceptance 6: ON the surface is measured, OFF the surface never is --------------------


def test_any_param_on_the_surface_is_measured(monkeypatch, tmp_path):
    """A surface function with an `Any` parameter is flagged (>=1)."""
    path = _write(
        tmp_path, "mod.py", "from typing import Any\n\n\ndef f(x: Any) -> int:\n    return 0\n"
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    measured = lean_surface_types.measure_surface_types()
    assert measured == {"mod.py::f": 1}


def test_identical_function_off_the_surface_is_never_measured(monkeypatch, tmp_path):
    """`g`, the identical `Any`-parameter shape as `f` but unreachable through any `__all__`
    (only `f`'s entry is on the mocked surface, in the SAME file so its tree is loaded either
    way), is never measured -- only `resolve_surface_names`'s own entries scope what
    `measure_surface_types` looks at, never "every def found in a file it happens to open".
    """
    path = _write(
        tmp_path,
        "mod.py",
        "from typing import Any\n\n\n"
        "def f(x: Any) -> int:\n    return 0\n\n\n"
        "def g(x: Any) -> int:\n    return 0\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    measured = lean_surface_types.measure_surface_types()
    assert measured == {"mod.py::f": 1}
    assert "mod.py::g" not in measured


# --- One test per violation kind ------------------------------------------------------------


def test_bare_dict_param_is_flagged(monkeypatch, tmp_path):
    """A bare, unparameterised `dict` parameter is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x: dict) -> int:\n    return 0\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


def test_bare_list_param_is_flagged(monkeypatch, tmp_path):
    """A bare, unparameterised `list` parameter is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x: list) -> int:\n    return 0\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


def test_bare_tuple_param_is_flagged(monkeypatch, tmp_path):
    """A bare, unparameterised `tuple` parameter is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x: tuple) -> int:\n    return 0\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


def test_object_return_is_flagged(monkeypatch, tmp_path):
    """An `object` return annotation is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x: int) -> object:\n    return x\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


def test_missing_param_annotation_is_flagged(monkeypatch, tmp_path):
    """A parameter with no annotation at all is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x) -> int:\n    return 0\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


def test_missing_return_annotation_is_flagged(monkeypatch, tmp_path):
    """A function with no return annotation at all is flagged."""
    path = _write(tmp_path, "mod.py", "def f(x: int):\n    return x\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


# --- Parameterized dict/list/tuple pass; the nested case still flags -----------------------


def test_fully_parameterized_dict_list_tuple_do_not_flag(monkeypatch, tmp_path):
    """`dict[str, int]`, `list[int]`, `tuple[int, ...]`: fully parameterised, never flagged."""
    path = _write(
        tmp_path,
        "mod.py",
        "def f(a: dict[str, int], b: list[int], c: tuple[int, ...]) -> None:\n    return None\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {}


def test_nested_bare_dict_inside_list_is_flagged(monkeypatch, tmp_path):
    """`list[dict]`: the outer `list[...]` is parameterised, but its inner `dict` is bare."""
    path = _write(tmp_path, "mod.py", "def f(x: list[dict]) -> None:\n    return None\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


# --- String forward-reference annotations ---------------------------------------------------


def test_quoted_any_forward_reference_is_flagged(monkeypatch, tmp_path):
    """A quoted forward-reference annotation (`'Any'`) is re-parsed and classified the same way."""
    path = _write(tmp_path, "mod.py", "def f(x: 'Any') -> int:\n    return 0\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "f"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::f": 1}


# --- Methods on a surface class --------------------------------------------------------------


def test_public_method_on_surface_class_is_flagged(monkeypatch, tmp_path):
    """A surface class's own public method with an `Any` parameter is flagged as `Class.method`."""
    path = _write(
        tmp_path,
        "mod.py",
        "from typing import Any\n\n\nclass C:\n    def m(self, x: Any) -> int:\n        return 0\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::C.m": 1}


def test_self_and_cls_params_are_never_flagged(monkeypatch, tmp_path):
    """`self`'s own missing annotation is never counted -- only real, unannotated parameters are."""
    path = _write(
        tmp_path,
        "mod.py",
        "class C:\n    def m(self, x: int) -> int:\n        return x\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_surface_types() == {}


def test_init_is_the_one_dunder_read_and_others_are_not(monkeypatch, tmp_path):
    """`__init__` with an `Any` parameter is flagged as `Class.__init__`; `__repr__` is not."""
    path = _write(
        tmp_path,
        "mod.py",
        "from typing import Any\n\n\nclass C:\n"
        "    def __init__(self, x: Any) -> None:\n        pass\n\n"
        "    def __repr__(self, x: Any) -> str:\n        return ''\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_surface_types() == {"mod.py::C.__init__": 1}


# --- measure_record_field_types --------------------------------------------------------------


def test_record_field_any_is_flagged(monkeypatch, tmp_path):
    """A `@record`-decorated surface class's own `Any`-typed field is flagged."""
    path = _write(
        tmp_path,
        "mod.py",
        "from typing import Any\n\nfrom fransys_model.kernel import record\n\n\n"
        '@record(kind="x")\nclass C:\n    a: Any\n',
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_record_field_types() == {"mod.py::C": 1}


def test_record_field_bare_dict_is_flagged(monkeypatch, tmp_path):
    """A `@value`-decorated surface class's own bare-`dict`-typed field is flagged."""
    path = _write(
        tmp_path,
        "mod.py",
        "from fransys_model.kernel import value\n\n\n@value\nclass C:\n    a: dict\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_record_field_types() == {"mod.py::C": 1}


def test_record_field_fully_typed_does_not_flag(monkeypatch, tmp_path):
    """A `@value` class whose fields are all fully annotated is never flagged."""
    path = _write(
        tmp_path,
        "mod.py",
        "from fransys_model.kernel import value\n\n\n@value\nclass C:\n    a: int\n    b: str\n",
    )
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_record_field_types() == {}


def test_plain_class_without_value_or_record_decorator_is_not_measured_as_a_record(
    monkeypatch, tmp_path
):
    """A surface class with no `@value`/`@record` decorator is never in `measure_record_field_
    types`'s output, even with an `Any`-typed field -- it is not a record.
    """
    path = _write(tmp_path, "mod.py", "from typing import Any\n\n\nclass C:\n    a: Any\n")
    _mock_surface(monkeypatch, tmp_path, (_entry(path, "C"),))
    assert lean_surface_types.measure_record_field_types() == {}


# --- Real workspace: report-only counts today -----------------------------------------------


def test_real_workspace_surface_types_are_report_only_today():
    """The real workspace has surface-type violations today (`Id[Any]` and similar); this check
    stays report-only until a later part routes it through `lean_ceilings` with a baseline.
    """
    measured = lean_surface_types.measure_surface_types()
    assert len(measured) > 0


def test_the_two_known_violators_are_closed_and_the_check_holds_them():
    """MS7's two known violators (`write_json(data: object)`, `SymbolPortError.__init__`'s
    `function: Id[Any]`) are typed now, and the check reads both signatures: `__init__` is
    measured (`test_init_is_the_one_dunder_read_and_others_are_not`), so one typed back to `Any`
    or `object` shows up here again.
    """
    # Positive first: layout's surface really does resolve to its three names, and the encode
    # module's `write_json` really is measured, so an empty answer is not an unread file.
    resolved = {entry.name for entry in lean_surface.resolve_surface_names(("fransys_layout",))}
    assert resolved == {"SymbolPortError", "lay_out_cables", "lay_out_schematic"}
    assert "write_json" in {
        entry.name for entry in lean_surface.resolve_surface_names(("fransys_model.kernel",))
    }
    measured = lean_surface_types.measure_surface_types()
    assert not any(site.startswith("packages/fransys-layout/") for site in measured)
    assert not any(site.endswith("kernel/encode.py::write_json") for site in measured)


@pytest.mark.parametrize(
    "fn", [lean_surface_types.measure_surface_types, lean_surface_types.measure_record_field_types]
)
def test_never_raises_on_the_real_workspace(fn):
    """Both measure functions run clean over the real workspace with no `modules` override."""
    fn()
