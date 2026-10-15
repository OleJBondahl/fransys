"""`d.layout.page_title` writes one `layout.page_title` and refuses what cannot be one."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Device, design, unit

from fransys_model.layout import PageTitle
from fransys_model.vocab import Unit

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
    with pytest.raises(
        AuthorError, match=r"takes a block, a function, a device, a strip or what d\.add returned"
    ):
        d.layout.page_title("F1", "Text")


class _One(NamedTuple):
    X1: Device


@unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="XX")
def _board(d) -> _One:
    return _One(d.device("X1", "DEMO-CONN-2P", interface=True))


def test_what_d_add_returned_gets_one_record_naming_its_unit() -> None:
    d = design(pair_library(), place="C1")
    nested = d.add(_board, "IO")
    d.layout.page_title(nested, "Board")
    (title,) = _titles(d)
    (model_unit,) = [r for r in d.draft().records() if isinstance(r, Unit)]
    assert (title.unit, title.block, title.function, title.item) == (
        model_unit.id,
        None,
        None,
        None,
    )
    with pytest.raises(AuthorError, match="already has a title"):
        d.layout.page_title(nested, "Again")


def test_a_tuple_d_add_did_not_return_is_refused() -> None:
    d = design(pair_library(), place="C1")
    d.add(_board, "IO")
    with pytest.raises(AuthorError, match=r"what d\.add returned"):
        d.layout.page_title(_One(d.device("X9", "DEMO-CONN-2P")), "Board")
