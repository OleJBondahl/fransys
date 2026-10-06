"""Field case: an item call with no tag takes the next free number of its class code.

The engineering shape: a cabinet adds spare terminal strips, a cable and a row of identical I/O
board modules in a loop, and wants no tag numbers to keep track of.

The bug: only `device` and `harness` took `None` for a tag. A strip, a cable and a unit instance
had to be given a written tag, and a loop of modules had to count for itself.

The rule (UT3), a strip taking the class code of its terminals' part (a strip with no terminal
has no part to name a code): `terminal_strip(None, part, name=)`, `cable(None, part, name=)` and
`d.add(definition, None, name=)` number from the class code, the part file's or the unit's own
(`class_code=` on `@fr.unit`). Instances and items of one code in a container share one count.
A floating call without `name=` raises, and so does a floating instance of a release with no
class code, naming both fixes.

The decision that fixes it: model-0134 (numbering) and author-0019 (the floating forms,
`class_code`).
"""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys_author import AuthorError

from fransys_model.vocab.tables import items


class _Io(NamedTuple):
    J1: fr.Device


def _board(class_code: str | None) -> Any:
    extra: dict[str, Any] = {} if class_code is None else {"class_code": class_code}

    @fr.unit(
        "demo-board",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AB",
        **extra,
    )
    def board(u: Any) -> _Io:
        root = u.device("U9", "DEMO-PCB-IO")
        return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True, unused=True))

    return board


@cache
def _coded() -> Any:
    return _board("U")


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


def test_a_loop_of_floating_instances_numbers_one_two_three() -> None:
    d = _design()
    for n in (1, 2, 3):
        d.add(_coded(), None, name=f"module{n}")
    model = fr.build(d).model
    assert [_text(model, f"module{n}", "J1") for n in (1, 2, 3)] == ["-U1-J1", "-U2-J1", "-U3-J1"]


def test_instances_and_devices_of_one_class_code_share_one_count() -> None:
    d = _design()
    d.device("U1", "DEMO-PCB-IO", name="carrier")
    d.add(_coded(), None, name="module")
    model = fr.build(d).model
    assert _text(model, "module", "J1") == "-U2-J1"


@pytest.mark.parametrize(
    "call",
    [
        lambda d: d.terminal_strip(None, "DEMO-TB-2.5"),
        lambda d: d.cable(None, "DEMO-CBL-4G1.5"),
        lambda d: d.add(_coded(), None),
    ],
    ids=["terminal_strip", "cable", "add"],
)
def test_a_floating_call_without_a_name_raises(call: Any) -> None:
    with pytest.raises(AuthorError, match=r"name="):
        call(_design())


def test_a_floating_instance_of_a_release_with_no_class_code_names_both_fixes() -> None:
    with pytest.raises(AuthorError) as raised:
        _design().add(_board(None), None, name="module")
    assert "class_code" in str(raised.value)
    assert "tag" in str(raised.value)
