"""V1's side order (layout-0102): power above signal, energy in above out, then AC above DC."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read import item_sides, side_facts

if TYPE_CHECKING:
    import pytest

_ANY: Any = None  # the model: the derive readers are patched, nothing else reads it


def _spec(function: str, port: str, *currents: str | None) -> Any:
    """A function spec with one port per V11 current given (one port with none if no current)."""
    ports = tuple(
        SimpleNamespace(port=port if n == 0 else f"{port}_{n}", current=one)
        for n, one in enumerate(currents or (None,))
    )
    return SimpleNamespace(function=function, ports=ports)


def _facts(
    monkeypatch: pytest.MonkeyPatch,
    *,
    takes: tuple[str, ...] = (),
    gives: tuple[str, ...] = (),
) -> None:
    """Patch what the facts read: who takes energy, who gives it."""
    monkeypatch.setattr(side_facts, "takes_energy", lambda _m, function: function in takes)
    monkeypatch.setattr(side_facts, "gives_energy", lambda _m, function: function in gives)


def test_a_dc_load_function_stands_above_an_ac_supply_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inverter: its DC input (a load) on top, its AC output (a supply) below."""
    _facts(monkeypatch, takes=("dc_in",), gives=("ac_out",))
    group = (_spec("dc_in", "p_in", "dc"), _spec("ac_out", "p_out", "ac"))
    assert item_sides.item_sides(_ANY, group) == {"p_in": "n", "p_out": "s"}


def test_ac_above_dc_still_orders_two_functions_of_one_energy_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _facts(monkeypatch, takes=("dc_in", "ac_in"))
    group = (_spec("dc_in", "p_dc", "dc"), _spec("ac_in", "p_ac", "ac"))
    assert item_sides.item_sides(_ANY, group) == {"p_ac": "n", "p_dc": "s"}


def test_a_supply_that_takes_energy_in_stands_above_a_supply_that_gives_it_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A redundancy module: its inputs are supply functions that take energy in (model-0131)."""
    _facts(monkeypatch, takes=("in_1",), gives=("out",))
    group = (_spec("in_1", "p_in"), _spec("out", "p_out"))
    assert item_sides.item_sides(_ANY, group) == {"p_in": "n", "p_out": "s"}


def test_v1a_a_power_function_stands_above_a_signal_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V1a alone: a function that gives energy out beats one that does neither."""
    _facts(monkeypatch, gives=("out",))
    group = (_spec("sig", "p_sig"), _spec("out", "p_out"))
    assert item_sides.item_sides(_ANY, group) == {"p_out": "n", "p_sig": "s"}


def test_v1b_energy_in_stands_above_energy_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """V1b alone: both are power functions, no AC; the one taking energy in is on top."""
    _facts(monkeypatch, takes=("in_1",), gives=("out",))
    group = (_spec("out", "p_out"), _spec("in_1", "p_in"))
    assert item_sides.side_rank(_ANY, group[1]) == (0, 0, 1)
    assert item_sides.item_sides(_ANY, group) == {"p_in": "n", "p_out": "s"}


def test_v1c_ac_stands_above_dc(monkeypatch: pytest.MonkeyPatch) -> None:
    """V1c alone: two signal functions that differ only in current kind."""
    _facts(monkeypatch)
    group = (_spec("dc", "p_dc", "dc"), _spec("ac", "p_ac", "ac"))
    assert item_sides.side_rank(_ANY, group[1]) == (1, 1, 0)
    assert item_sides.item_sides(_ANY, group) == {"p_ac": "n", "p_dc": "s"}


def test_v1c_reads_the_port_current_not_the_rating(monkeypatch: pytest.MonkeyPatch) -> None:
    """A function whose ports state no current is not AC, whatever its datasheet says."""
    _facts(monkeypatch)
    group = (_spec("a", "p_a"), _spec("b", "p_b", None))
    assert item_sides.item_sides(_ANY, group) == {}


def test_v1c_a_function_with_ac_and_dc_ports_is_not_ac(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rule: a port at AC and none at DC makes the function AC; a mix of both does not."""
    _facts(monkeypatch)
    group = (_spec("mixed", "p_mix", "ac", "dc"), _spec("ac", "p_ac", "ac"))
    assert item_sides.item_sides(_ANY, group) == {"p_ac": "n", "p_mix": "s", "p_mix_1": "s"}
