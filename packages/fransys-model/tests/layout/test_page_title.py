"""`layout.page_title`: one text for one block, function or item (PAGES-TITLES)."""

from dataclasses import replace
from typing import Any

import pytest
from layout_examples import drawn_function, function_id, group_node

from fransys_model.kernel import Draft, FreezeError, Id, Origin, SchemaError, dumps, freeze, loads
from fransys_model.layout import PageTitle


def _title(**thing: Any) -> PageTitle:
    return PageTitle(
        id=Id(kind="layout.page_title", value="b" * 32),
        key=("examples", "page_title", "b"),
        text="Field terminals",
        **thing,
    )


def _freeze(title: PageTitle):
    draft = Draft()
    draft.extend(
        (group_node(), *drawn_function(), title),
        origin=Origin(file="test_page_title.py", line=1, note="fixture"),
    )
    return freeze(draft)


def test_a_title_for_each_thing_kind_freezes_and_round_trips() -> None:
    item, function = drawn_function()
    for thing in ({"block": group_node().id}, {"function": function.id}, {"item": item.id}):
        model = _freeze(_title(**thing))
        assert loads(dumps(model)) == model


@pytest.mark.parametrize("things", [0, 2])
def test_a_title_names_exactly_one_thing(things: int) -> None:
    item, function = drawn_function()
    named = {"function": function.id, "item": item.id}
    with pytest.raises(SchemaError):
        _title(**dict(list(named.items())[:things]))


def test_a_title_has_text() -> None:
    with pytest.raises(SchemaError):
        replace(_title(block=group_node().id), text="  ")


def test_a_title_for_a_thing_the_model_lacks_is_refused() -> None:
    with pytest.raises(FreezeError):
        _freeze(_title(function=function_id("z")))
