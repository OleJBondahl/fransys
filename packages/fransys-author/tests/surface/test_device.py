"""EA4 runtime half: `device`, typed and string parts, and checked pin and function access."""

from typing import Any, ClassVar

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Device, Fn, TypedDevice, design

from fransys_model.vocab import AspectNode, Placement, PlcRequestFacet, SignalType
from fransys_model.vocab import Item as ModelItem
lazy from fransys_model.kernel import Draft


class Relay(TypedDevice):
    mpn: ClassVar[str] = "TEST-RLY-2CO"


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def _relay(parts: Draft, **kw):
    d = design(parts, place="C1")
    return d, d.device("K1", "TEST-RLY-2CO", **kw)


def test_a_device_is_a_device_and_writes_an_item_with_its_tag(parts: Draft) -> None:
    d, k1 = _relay(parts)
    assert isinstance(k1, Device)
    (item,) = _records(d, ModelItem)
    assert item.tag == "K1"


def test_a_part_class_gives_that_class_and_its_mpn(parts: Draft) -> None:
    d = design(parts)
    k1 = d.device("K1", Relay)
    assert isinstance(k1, Relay)
    typed: Any = k1  # a generated class declares its pins for ty; this test class does not
    assert typed.coil["A1"].name == "A1"


def test_a_part_without_mpn_or_not_a_device_class_raises(parts: Draft) -> None:
    class NoMpn(TypedDevice):
        pass

    d = design(parts)
    for bad in (NoMpn, int, 7):
        with pytest.raises(AuthorError, match="MPN string or a part class with an mpn"):
            d.device("K1", bad)  # type: ignore[arg-type]  # ty: ignore[no-matching-overload] -- planted bad part


def test_an_unknown_mpn_raises_naming_the_candidates(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="TEST-RLY-2CO"):
        design(parts).device("K1", "TEST-RLY-2C")


def test_a_prefixed_tag_raises_naming_the_call(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="write Q1; device\\(\\) adds the -"):
        design(parts).device("-Q1", "TEST-RLY-2CO")
    with pytest.raises(AuthorError, match="write Q1; device\\(\\) adds the -"):
        design(parts).device("=Q1", "TEST-RLY-2CO")


def test_a_device_needs_a_tag_or_a_name(parts: Draft) -> None:
    d = design(parts)
    with pytest.raises(AuthorError, match="give a tag, or name="):
        d.device(None, "TEST-RLY-2CO")
    assert d.device(None, "TEST-RLY-2CO", name="run").coil is not None
    assert _records(d, ModelItem)[0].tag is None


def test_a_duplicate_tag_raises_in_one_function_not_across_two(parts: Draft) -> None:
    d = design(parts)
    with d.function("P1", "a"):
        d.device("K1", "TEST-RLY-2CO")
        with pytest.raises(AuthorError, match="tag 'K1' is already used in function 'P1'"):
            d.device("K1", "TEST-RLY-2CO")
    with d.function("P2", "b"):
        d.device("K1", "TEST-RLY-2CO")
    assert len(_records(d, ModelItem)) == 2
    assert {i.key[0] for i in _records(d, ModelItem)} == {"P1/K1", "P2/K1"}


def test_place_defaults_overrides_and_none(parts: Draft) -> None:
    d = design(parts, place="C1")
    d.device("K1", "TEST-RLY-2CO")
    d.device("K2", "TEST-RLY-2CO", place="EXT")
    d.device("K3", "TEST-RLY-2CO", place=None)
    labels = {n.id: n.label for n in _records(d, AspectNode)}
    where = {
        i.key[0]: [labels[p.node] for p in _records(d, Placement) if p.item == i.id]
        for i in _records(d, ModelItem)
    }
    assert where == {"K1": ["C1"], "K2": ["EXT"], "K3": []}


def test_a_device_in_a_function_block_is_placed_in_the_function(parts: Draft) -> None:
    d = design(parts)
    with d.function("M1", "Starter"):
        d.device("K1", "TEST-RLY-2CO")
    d.device("K2", "TEST-RLY-2CO")
    labels = {n.id: n.label for n in _records(d, AspectNode)}
    found = {p.item: labels[p.node] for p in _records(d, Placement)}
    assert sorted(found.values()) == ["M1"]


def test_a_parent_device_is_the_items_parent(parts: Draft) -> None:
    d = design(parts)
    k1 = d.device("K1", "TEST-RLY-2CO")
    d.device("K2", "TEST-RLY-2CO", parent=k1)
    parents = {i.key[0]: i.parent for i in _records(d, ModelItem)}
    assert parents["K2"] == k1._item.id
    assert parents["K1"] is None


def test_interface_outside_a_unit_raises_the_engines_error(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="needs a unit"):
        design(parts).device("K1", "TEST-RLY-2CO", interface=True)


def test_a_function_by_attribute_and_a_pin_by_attribute_name_or_integer(parts: Draft) -> None:
    _, k1 = _relay(parts)
    assert isinstance(k1.coil, Fn)
    assert k1.coil.A1 is k1.coil["A1"] or k1.coil["A1"] == k1.coil.A1
    assert k1.no_1[13] == k1.no_1["13"] == k1["13"] == k1[13]
    assert k1["A2"] == k1.A2  # a pin name, unique on the device


def test_an_unknown_function_raises_and_lists_the_functions(parts: Draft) -> None:
    _, k1 = _relay(parts)
    with pytest.raises(AuthorError) as err:
        _ = k1.coli
    assert str(err.value) == "K1 has no function or pin 'coli'; functions: co_2, coil, no_1"


def test_an_unknown_pin_raises_and_lists_the_pins(parts: Draft) -> None:
    _, k1 = _relay(parts)
    with pytest.raises(AuthorError, match=r"K1 has no pin '9'; pins: 13, 14, 21, 22, 24, A1, A2"):
        _ = k1[9]
    with pytest.raises(AuthorError, match=r"K1\.coil has no pin 'A3'; pins: A1, A2"):
        _ = k1.coil["A3"]
    with pytest.raises(AuthorError, match=r"K1\.coil has no pin 'A3'; pins: A1, A2"):
        _ = k1.coil.A3


def test_an_ambiguous_pin_names_its_functions_and_a_function_resolves_it(parts: Draft) -> None:
    d = design(parts)
    c1 = d.device("C1", "TEST-CLASH")
    with pytest.raises(AuthorError, match=r"C1 pin '13' is on functions co_1, co_2; say C1\.<f"):
        _ = c1[13]
    assert c1.co_1[13].name == "13"
    assert c1.co_2[13] != c1.co_1[13]


def test_private_names_are_not_functions_or_pins(parts: Draft) -> None:
    _, k1 = _relay(parts)
    with pytest.raises(AttributeError):
        _ = k1._nope
    with pytest.raises(AttributeError):
        _ = k1.coil._nope


def test_plc_and_scale_reach_the_engine_function(parts: Draft) -> None:
    d, k1 = _relay(parts)
    assert k1.coil.plc(SignalType.DO, "Pump run") is not None
    (request,) = _records(d, PlcRequestFacet)
    assert (request.signal.value, request.signal_name) == ("do", "Pump run")
    k1.coil.scale("bar", raw=(0, 100), eng=("0", "10"))
