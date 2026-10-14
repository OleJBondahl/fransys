"""`d.layout.page_title` writes one `layout.page_title` and refuses what cannot be one."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.layout import PageTitle

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


def _titles(d):
    return [r for r in d.draft().records() if isinstance(r, PageTitle)]


def _design():
    d = design(pair_library(), place="C1")
    with d.function("F1", "One") as group:
        device = d.device("X1", "DEMO-CONN-2P")
    return d, group, device


def test_a_block_a_function_and_a_device_each_get_one_record() -> None:
    d, group, device = _design()
    fn = getattr(device, device._item.functions[0].name)
    for thing, text in ((group, "Block"), (fn, "Function"), (device, "Device")):
        d.layout.page_title(thing, text)
    found = {r.text: r for r in _titles(d)}
    assert found["Block"].block == group.id
    assert found["Function"].function == fn._fn.id
    assert found["Device"].item == device.id


def test_an_empty_text_is_refused() -> None:
    d, group, _ = _design()
    with pytest.raises(AuthorError, match="empty"):
        d.layout.page_title(group, "  ")


def test_a_second_title_on_one_thing_is_refused() -> None:
    d, group, _ = _design()
    d.layout.page_title(group, "One")
    with pytest.raises(AuthorError, match="already has a title"):
        d.layout.page_title(group, "Two")


def test_a_thing_that_is_none_of_the_three_is_refused() -> None:
    d, _, _ = _design()
    with pytest.raises(AuthorError, match="takes a block, a function or a device"):
        d.layout.page_title("F1", "Text")
