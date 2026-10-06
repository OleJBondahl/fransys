"""EA-PARTS P3: `design` checks a generated parts module's digest, then makes a `Design`."""

import shutil
from pathlib import Path
from types import SimpleNamespace

import demo_parts
import fransys as fr
import pytest
from fransys.design import design
from fransys.parts_module import library_digest
from fransys.pipeline import parts
from fransys_author import AuthorError

from fransys_model.kernel import freeze

PART = "parts/lamp-24v.toml"


def _digest(draft) -> str:
    return freeze(draft).digest


def _module(*sources: str, digest: str | None = None):
    return SimpleNamespace(
        SOURCES=sources, LIBRARY_DIGEST=digest or library_digest(*sources), __name__="gen_parts"
    )


def _plant(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "plant_parts"
    shutil.copytree(
        Path(demo_parts.__file__).parent, root, ignore=shutil.ignore_patterns("__pycache__")
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    return root / PART


def _assert_demo_library(d) -> None:
    assert isinstance(d, fr.Design)
    assert _digest(d.library) == _digest(parts("demo_parts"))


def test_fresh_module_makes_a_surface_design_with_the_loaded_library() -> None:
    _assert_demo_library(design(_module("demo_parts"), place="C1"))


def test_stale_module_raises_with_the_regenerate_command() -> None:
    with pytest.raises(AuthorError) as caught:
        design(_module("demo_parts", digest="0" * 64))
    assert "python -m fransys parts-module" in str(caught.value)
    assert "demo_parts" in str(caught.value)


def test_string_path_needs_no_module() -> None:
    _assert_demo_library(design("demo_parts", place="C1"))


def test_changed_fact_makes_the_module_stale_and_whitespace_does_not(tmp_path, monkeypatch) -> None:
    part = _plant(tmp_path, monkeypatch)
    module = _module("plant_parts")
    design(module)

    part.write_text(part.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    design(module)

    part.write_text(part.read_text(encoding="utf-8").replace('"2.4"', '"3.0"'), encoding="utf-8")
    with pytest.raises(AuthorError, match="plant_parts"):
        design(module)


def test_package_exports_the_facade_design() -> None:
    assert "design" in fr.__all__
    assert fr.design is design
