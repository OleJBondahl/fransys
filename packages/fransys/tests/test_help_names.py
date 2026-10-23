"""`help KEY` for a public name: signature, docstring first line and a guide page (AGENT-HELP)."""

import importlib.resources
import inspect
from functools import cache
lazy from collections.abc import Callable

import fransys
import pytest
from fransys._help_names import _guide_pages, names_text, resolve


@pytest.fixture(scope="module")
def text_of() -> Callable[[str], str]:
    """The printed help of a key, built once per key and only when a test asks for it."""

    @cache
    def text(key: str) -> str:
        found = resolve(key)
        assert found is not None, key
        return names_text(found)

    return text


@pytest.mark.parametrize("key", ["write", "fr.write", "d.device", "MergeConflict"])
def test_a_name_prints_signature_docstring_and_guide_page(text_of, key):
    text = text_of(key)
    assert "(" in text.splitlines()[0]
    assert "guide: " in text
    assert ".md" in text


@pytest.mark.parametrize("key", ["write", "MergeConflict"])
def test_the_docstring_first_line_is_printed(text_of, key):
    doc = inspect.getdoc(getattr(fransys, key)) or ""
    assert doc.splitlines()[0] in text_of(key)


def test_a_method_signature_leaves_out_self(text_of):
    assert "self" not in text_of("d.device").splitlines()[0]
    assert "self" not in text_of("d.detail.wire").splitlines()[0]


def test_a_constant_and_an_unknown_name():
    found = resolve("ABOVE")
    assert found is not None
    assert "constant" in found.signature
    assert resolve("wrte") is None
    assert resolve("d.nope") is None


def test_every_guide_page_is_linked_from_the_index():
    """The reading order is `index.md`'s links, so a page it does not name is never searched."""
    guide = importlib.resources.files("fransys").joinpath("guide")
    on_disk = {p.name for p in guide.iterdir() if p.name.endswith(".md")}
    assert on_disk == {name for name, _ in _guide_pages()}


def test_the_first_page_in_reading_order_that_names_a_thing_wins():
    assert _guide_pages()[0][0] == "index.md"
