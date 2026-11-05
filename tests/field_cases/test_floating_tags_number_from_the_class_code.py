"""Field case: a cabinet adds spare terminal strips and a cable, with no tag numbers given.
The bug: only device and harness took None for a tag, so a strip and a cable needed a written tag.
Fixed by model-0134 and author-0019, each takes the next free number of its part class code (no unit instance form, R1494)."""

from typing import Any

import fransys as fr
import pytest
from fransys_author import AuthorError

from fransys_model.vocab.tables import items


def _design() -> Any:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    return d


def _text(model: fr.Model, *tail: str) -> str:
    """The printed designation of the one item whose key ends with `tail`."""
    (item,) = (i for i in items(model).values() if i.key[-len(tail) :] == tail)
    return fr.derive.printed_designation(model, item.id)


def test_floating_strips_number_from_their_terminal_part_class_code() -> None:
    d = _design()
    d.terminal_strip(None, "DEMO-TB-2.5", 1, name="spare")
    d.terminal_strip(None, "DEMO-TB-2.5", 1, name="spare2")
    model = fr.build(d).model
    assert _text(model, "spare") == "-X1"
    assert _text(model, "spare2") == "-X2"


def test_a_floating_cable_numbers_from_its_part_class_code() -> None:
    d = _design()
    d.cable(None, "DEMO-CBL-4G1.5", name="w")
    assert _text(fr.build(d).model, "w") == "-W1"


@pytest.mark.parametrize(
    "call",
    [
        lambda d: d.terminal_strip(None, "DEMO-TB-2.5"),
        lambda d: d.cable(None, "DEMO-CBL-4G1.5"),
    ],
    ids=["terminal_strip", "cable"],
)
def test_a_floating_call_without_a_name_raises(call: Any) -> None:
    with pytest.raises(AuthorError, match=r"name="):
        call(_design())
