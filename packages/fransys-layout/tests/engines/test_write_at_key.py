"""Decision layout-0216 and model-0220: a copy drawn at its wire is keyed by the function
it stands at."""

from fransys_layout.engines.schematic.write.keys import WriteKeys
from fransys_layout.engines.schematic.write.placements import _at
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Function

_K1 = make_id(Function, ("k1",))
_K2 = make_id(Function, ("k2",))


def _keys(function: dict) -> WriteKeys:
    return WriteKeys(
        function=function,
        port={},
        conductor={},
        item={},
        unit={},
        aspect_node={},
        port_function={},
        port_name={},
        item_function={},
    )


def test_a_copy_at_no_host_adds_no_key_part() -> None:
    """A copy with no host function gets an empty key part."""
    assert _at(_keys({}), None) == ()


def test_two_copies_at_two_hosts_get_two_keys() -> None:
    """Copies at two functions get two different keys, each starting with "at"."""
    keys = _keys({_K1: ("K1",), _K2: ("K2",)})
    first, second = _at(keys, _K1), _at(keys, _K2)
    assert first
    assert first[0] == "at"
    assert second
    assert second[0] == "at"
    assert first != second


def test_the_key_holds_the_hosts_function_key() -> None:
    """The key part is "at" followed by the host function's own key."""
    assert _at(_keys({_K1: ("K1",)}), _K1) == ("at", "K1")
