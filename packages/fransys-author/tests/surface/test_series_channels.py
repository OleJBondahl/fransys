"""A series takes a PLC module's lowest free channel of the path's direction and kind (C6.5)."""

from typing import TYPE_CHECKING, Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import AI, DI, DO, design

from fransys_model.kernel import make_id
from fransys_model.vocab import Conductor, FunctionKind, PartCategory, PlcChannelFacet, SignalType

from ..conftest import _ORIGIN, _function, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import _pin, series_library  # noqa: TID252 -- same

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

WIRE = ("BK", 2.5)
CHANNELS = (
    ("di_1", "I1", SignalType.DI, 1),
    ("di_2", "I2", SignalType.DI, 2),
    ("do_1", "O1", SignalType.DO, 1),
    ("do_2", "O2", SignalType.DO, 2),
    ("ai_1", "AI1", SignalType.AI_CURRENT, 1),
)


def _module(draft: Draft, mpn: str, kept: tuple[str, ...]) -> None:
    """A PLC module with the channel functions named in `kept`, one pin each."""
    library = _library(draft, f"lib-{mpn}")
    part = _part(
        draft, library, manufacturer="TestCo", mpn=mpn,
        category=PartCategory.PLC_MODULE, letter="A",
    )  # fmt: skip
    for name, pin, signal, number in CHANNELS:
        if name not in kept:
            continue
        function = _function(draft, part, name, FunctionKind.PLC_CHANNEL)
        _pin(draft, function, pin)
        key = (*function.key, "plc_channel")
        facet = PlcChannelFacet(
            id=make_id(PlcChannelFacet, key), key=key, subject=function.id,
            signal=signal, channel=number,
        )  # fmt: skip
        draft.add(facet, origin=_ORIGIN)


@pytest.fixture(scope="module")
def lib() -> Draft:
    draft = series_library()
    _module(draft, "TEST-PLC-IO", ("di_1", "di_2", "do_1", "do_2"))
    _module(draft, "TEST-PLC-MIX", ("di_1", "ai_1", "do_1"))
    _module(draft, "TEST-PLC-IN", ("di_1",))
    return draft


def _wired(d: Design, *pins: object) -> bool:
    """Whether a conductor ends at every pin of `pins`."""
    ends = {end for r in d.draft().records() if isinstance(r, Conductor) for end in (r.a, r.b)}
    return all(pin.id in ends for pin in pins)  # ty: ignore[unresolved-attribute] -- a pin has an id


def _button(d: Design, tag: str) -> Any:
    return d.device(tag, "TEST-BTN-NO")


def test_paths_ending_at_a_module_take_its_inputs_in_call_order(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1 = d.device("A1", "TEST-PLC-IO")
    d.series(_button(d, "S1").contact, a1, wire=WIRE)
    assert _wired(d, a1.di_1["I1"])
    assert not _wired(d, a1.di_2["I2"])
    d.series(_button(d, "S2").contact, a1, wire=WIRE)
    assert _wired(d, a1.di_2["I2"])


def test_a_fixed_channel_is_taken_and_a_later_call_skips_it(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1 = d.device("A1", "TEST-PLC-IO")
    d.series(_button(d, "S1").contact, a1.di_1, wire=WIRE)
    d.series(_button(d, "S2").contact, a1, wire=WIRE)
    assert _wired(d, a1.di_2["I2"])


def test_a_module_with_every_channel_taken_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1 = d.device("A1", "TEST-PLC-IN")
    d.series(_button(d, "S1").contact, a1, wire=WIRE)
    with pytest.raises(AuthorError, match="every di channel of A1 is taken"):
        d.series(_button(d, "S2").contact, a1, wire=WIRE)


def test_a_path_starting_at_a_module_takes_its_lowest_free_output(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1, k1 = d.device("A1", "TEST-PLC-IO"), d.device("K1", "TEST-KM-3P")
    d.series(a1, k1.coil, wire=WIRE)
    assert _wired(d, a1.do_1["O1"])
    assert not _wired(d, a1.di_1["I1"])


def test_a_module_in_the_middle_of_a_path_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1 = d.device("A1", "TEST-PLC-IO")
    with pytest.raises(AuthorError, match="middle of a path"):
        d.series(_button(d, "S1").contact, a1, _button(d, "S2").contact, wire=WIRE)


def test_a_module_with_no_channel_this_way_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1, k1 = d.device("A1", "TEST-PLC-IN"), d.device("K1", "TEST-KM-3P")
    with pytest.raises(AuthorError, match="A1 has no PLC output"):
        d.series(a1, k1.coil, wire=WIRE)


def test_two_kinds_and_no_request_raises_naming_both(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1 = d.device("A1", "TEST-PLC-MIX")
    with pytest.raises(AuthorError, match=r"ai_current and di inputs.*fr\.AI.*fr\.DI"):
        d.series(_button(d, "S1").contact, a1, wire=WIRE)


def test_a_request_settles_the_kind(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1, s1 = d.device("A1", "TEST-PLC-MIX"), _button(d, "S1")
    s1.contact.plc(AI, "Level")
    d.series(s1.contact, a1, wire=WIRE)
    assert _wired(d, a1.ai_1["AI1"])
    assert not _wired(d, a1.di_1["I1"])


def test_a_request_the_module_cannot_serve_this_way_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1, s1 = d.device("A1", "TEST-PLC-MIX"), _button(d, "S1")
    s1.contact.plc(DO, "Wrong way")
    with pytest.raises(AuthorError, match="A1 has no do input for the request 'Wrong way'"):
        d.series(s1.contact, a1, wire=WIRE)


def test_a_request_farther_along_the_path_still_settles_the_kind(lib: Draft) -> None:
    d = design(lib, place="C1")
    a1, s1, s2 = d.device("A1", "TEST-PLC-MIX"), _button(d, "S1"), _button(d, "S2")
    s1.contact.plc(DI, "Start")
    d.series(s1.contact, s2.contact, a1, wire=WIRE)
    assert _wired(d, a1.di_1["I1"])
