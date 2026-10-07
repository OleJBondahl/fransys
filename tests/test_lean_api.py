"""`scripts/lean_api.py`: `api`, `_package_modules` (MS9, `just api <package>`).

Loaded like `test_lean_surface_types.py` loads `scripts/lean_surface_types.py`
(`importlib.util.spec_from_file_location`), since the script is not a package module. The
acceptance-8 and model tests read the real installed workspace (this order's own point: build on
demand, never store the surface separately) rather than a mocked fixture.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import fransys
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


lean_api = _load("fransys_lean_api_under_test", "lean_api.py")

_HEADER_RE = re.compile(r"^(fransys[\w.]*)\.(\w+)", re.MULTILINE)


def _headers(output: str) -> list[tuple[str, str]]:
    """Every `(module, name)` a printed block's own header line names, in order."""
    return _HEADER_RE.findall(output)


def test_fransys_pdf_gives_exactly_its_seven_surface_names():
    """Acceptance 8: `fransys_pdf`'s `__all__` has 7 names; `api()` prints exactly those 7,
    including `PRESET_PAGES`, a plain data value with no signature of its own.
    """
    import fransys_pdf

    assert tuple(fransys_pdf.__all__) == (
        "PRESET_PAGES",
        "check",
        "document_pages",
        "font_dir",
        "page_kinds",
        "requests_harness_pages",
        "source",
    )
    output = lean_api.api("fransys_pdf")
    headers = _headers(output)
    assert [name for _module, name in headers] == list(fransys_pdf.__all__)
    assert all(module == "fransys_pdf" for module, _name in headers)


def test_fransys_pdf_output_is_byte_identical_across_two_calls():
    """Acceptance 8's other half: two calls on the same commit print the same bytes."""
    assert lean_api.api("fransys_pdf") == lean_api.api("fransys_pdf")


def test_model_package_maps_to_its_nine_surface_modules():
    """`_package_modules("fransys_model")` is exactly MS1's nine dotted modules, sorted --
    the general prefix rule, not a special case for the model.
    """
    assert lean_api._package_modules("fransys_model") == (
        "fransys_model.derive",
        "fransys_model.derive.baseline",
        "fransys_model.derive.block_diagram",
        "fransys_model.derive.cable_drawing",
        "fransys_model.derive.drawing_text",
        "fransys_model.derive.numbering_pins",
        "fransys_model.kernel",
        "fransys_model.layout",
        "fransys_model.vocab",
    )


def test_model_api_output_covers_all_nine_modules_own_names():
    """`api("fransys_model")` prints at least one header per one of the nine modules."""
    output = lean_api.api("fransys_model")
    modules_seen = {module for module, _name in _headers(output)}
    assert modules_seen == {
        "fransys_model.derive",
        "fransys_model.derive.baseline",
        "fransys_model.derive.block_diagram",
        "fransys_model.derive.cable_drawing",
        "fransys_model.derive.drawing_text",
        "fransys_model.derive.numbering_pins",
        "fransys_model.kernel",
        "fransys_model.layout",
        "fransys_model.vocab",
    }


def test_fransys_maps_to_itself_and_its_colours_submodule():
    """`fransys`'s own surface also picks up `fransys.colours` (MS8), by the same prefix
    rule, with no special case.
    """
    assert lean_api._package_modules("fransys") == ("fransys", "fransys.colours")


def test_unknown_package_fails_with_a_one_line_message():
    """A package name owning no surface module raises with exactly one line of message."""
    with pytest.raises(lean_api.UnknownPackageError) as excinfo:
        lean_api.api("not_a_real_package")
    message = str(excinfo.value)
    assert "\n" not in message
    assert "not_a_real_package" in message


def test_data_value_is_printed_with_no_signature_or_docstring():
    """`PRESET_PAGES` (a `frozendict`, not a def) prints as a bare header naming its type."""
    output = lean_api.api("fransys_pdf")
    preset_line = next(
        line for line in output.splitlines() if line.startswith("fransys_pdf.PRESET_PAGES")
    )
    assert preset_line == "fransys_pdf.PRESET_PAGES (frozendict)"


def test_a_function_prints_a_real_signature():
    """`fransys_pdf.check`, a real function, prints a `(...)`-style call signature."""
    output = lean_api.api("fransys_pdf")
    check_line = next(line for line in output.splitlines() if line.startswith("fransys_pdf.check("))
    assert check_line == (
        "fransys_pdf.check(model: Model, svgs: Mapping[str, str]) -> tuple[Finding, ...]"
    )


@pytest.mark.parametrize("module_path", ["fransys", "fransys_model.derive"])
def test_md_page_lists_every_name_of_all_exactly_once(module_path):
    """FS5 acceptance 4: the markdown page has one `###` heading per `__all__` name, no more."""
    import importlib

    module = importlib.import_module(module_path)
    headings = re.findall(r"^### (\w+)$", lean_api.api_md(module_path), re.MULTILINE)
    assert sorted(headings) == sorted(module.__all__)
    assert len(headings) == len(set(headings))


def test_md_entry_has_signature_in_code_block():
    """A function's entry is its heading, then its `def` line in a python code block."""
    page = lean_api.api_md("fransys")
    assert re.search(r"### write\n\n```python\ndef write\(.*\)", page)


def test_md_page_groups_names_by_kind_each_group_sorted():
    """FS5: three `## ` groups in order; every `__all__` name once; names sorted within a group."""
    page = lean_api.api_md("fransys")
    assert re.findall(r"^## (.+)$", page, re.MULTILINE) == ["Functions", "Classes", "Constants"]
    _, functions, classes, constants = re.split(r"^## .+$", page, flags=re.MULTILINE)
    seen = []
    for chunk in (functions, classes, constants):
        names = re.findall(r"^### (\w+)$", chunk, re.MULTILINE)
        assert names == sorted(names)
        seen += names
    assert sorted(seen) == sorted(fransys.__all__)
    assert "def write(" in functions
    assert "\nclass " in classes


@pytest.mark.parametrize("module_path", ["fransys", "fransys_model.derive"])
def test_no_signature_shows_a_private_module_path(module_path):
    """A surface signature prints `Design`, never `_args.Design`: both the md page and the text."""
    page = lean_api.api_md(module_path)
    signatures = re.findall(r"^def .*$", page, re.MULTILINE)
    assert signatures, "the page has function signatures to check"
    assert not [line for line in signatures if re.search(r"\b_\w+\.\w", line)]


def test_build_signature_prints_design_in_text_and_md():
    """`build`'s `_args.Design` annotation prints as the surface name `Design`."""
    assert "def build(*drafts: Draft | Design, " in lean_api.api_md("fransys")
    assert "(*drafts: Draft | Design, " in lean_api.api("fransys")
