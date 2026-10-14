"""One guard for a designation read before numbering: the item, pin and function reads share it."""

from typing import Any

import pytest

from fransys_layout.engines.schematic.read import functions, views
from fransys_layout.engines.schematic.read.text_or_empty import text_or_empty
from fransys_model.kernel import SchemaError


def _refuses(_model: Any, _ident: Any) -> str:
    message = "no tag yet"
    raise SchemaError(message, kind="item")


def _says(_model: Any, _ident: Any) -> str:
    return "-K1"


def test_a_text_is_passed_through_and_a_refusal_is_empty() -> None:
    stub: Any = None  # the callables ignore the model and the id
    assert text_or_empty(_says, stub, stub) == "-K1"
    assert text_or_empty(_refuses, stub, stub) == ""


@pytest.mark.parametrize(
    ("module", "name", "call"),
    [
        (views, "item_tag_text", views.item_text),
        (views, "port_designation", views.pin_text),
        (functions, "reference_designation", functions._designation),
    ],
)
def test_each_view_read_answers_empty_when_the_designation_refuses(
    monkeypatch: pytest.MonkeyPatch, module: Any, name: str, call: Any
) -> None:
    monkeypatch.setattr(module, name, _refuses)
    assert call(None, None) == ""
    monkeypatch.setattr(module, name, _says)
    assert call(None, None) == "-K1"
