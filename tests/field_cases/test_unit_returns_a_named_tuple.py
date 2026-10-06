"""Field case: a unit returns a `NamedTuple` and `d.add` hands that same instance back.

The engineering shape: a cabinet unit exposing two boundary devices, one of them a terminal
strip's run, which the parent cabinet reads by name.

The bug: a unit returned a `dict[str, Device]`, so every boundary was typed `Device` and a
misspelt name was found at run time only.

The rule (EA15, owner "C1"): a unit function returns an instance of a `typing.NamedTuple`
class and `d.add` returns that instance. Any other return raises and shows the `NamedTuple`
form.
"""

from typing import NamedTuple

import fransys as fr
import pytest
from fransys_author import AuthorError


class _Cab(NamedTuple):
    X1: fr.Device
    L1: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(d: fr.Design) -> _Cab:
    strip = d.terminal_strip("X2", "DEMO-TB-2.5", 3, interface=True)
    return _Cab(d.device("X1", "DEMO-CONN-2P", interface=True), strip.run("L1", 2))


@fr.unit(  # ty: ignore[invalid-argument-type] -- a mapping return is the refusal under test
    "demo-dict", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
def _dict(d: fr.Design) -> dict[str, fr.Device]:
    return {"X1": d.device("X1", "DEMO-CONN-2P", interface=True)}


def test_add_returns_the_named_tuple_instance() -> None:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    cab = d.add(_cab, "CAB")
    assert isinstance(cab, _Cab)
    assert cab.X1 is not None
    assert cab.L1[1] is not None
    assert fr.build(d).model


def test_a_mapping_return_raises_and_shows_the_named_tuple_form() -> None:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    with pytest.raises(AuthorError, match=r"NamedTuple"):
        d.add(_dict, "CAB")
