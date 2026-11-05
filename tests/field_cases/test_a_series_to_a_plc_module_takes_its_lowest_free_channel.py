"""Field case: sixteen push buttons, each in series from a 24 V supply to one 16-channel digital input module, asking for a digital input.
The bug: the engineer wrote `a1.di_1` to `a1.di_16` by hand, so the channel map lived twice in the script.
Fixed by author-0047 (API-CLARITY C6.5), a module passed whole takes its lowest free channel; a fixed channel is skipped."""

from typing import Any

import fransys as fr
import pytest
from _field_designs import plc_di_design
from fransys.colours import BU

from fransys_model.derive import plc_channel_rows

COUNT = 16


def _button(d: fr.Design, dc: Any, target: Any, number: int) -> None:
    button = d.device(f"S{number}", "DEMO-PB-NC")
    button.sw.plc(fr.DI, f"Button {number}")
    d.series(dc.plus, button.sw, target, wire=(BU, 0.75))


def _channels(d: fr.Design) -> dict[str, str]:
    """The channel pin each named signal sits on."""
    rows = plc_channel_rows(fr.build(d).model)
    return {row.signal_name: row.pin for row in rows if row.signal_name}


def test_sixteen_buttons_in_io_list_order_take_channels_one_to_sixteen() -> None:
    d, dc, a1 = plc_di_design()
    for number in range(1, COUNT + 1):
        _button(d, dc, a1, number)
    assert _channels(d) == {f"Button {n}": f"-A1:{n}" for n in range(1, COUNT + 1)}


def test_a_fixed_channel_is_taken_and_the_next_calls_skip_it() -> None:
    d, dc, a1 = plc_di_design()
    _button(d, dc, a1.di_2, 9)
    _button(d, dc, a1, 1)
    _button(d, dc, a1, 2)
    assert _channels(d) == {"Button 9": "-A1:2", "Button 1": "-A1:1", "Button 2": "-A1:3"}


def test_a_module_in_the_middle_of_a_path_raises() -> None:
    d, dc, a1 = plc_di_design()
    button = d.device("S1", "DEMO-PB-NC")
    with pytest.raises(fr.AuthorError, match="middle of a path"):
        d.series(dc.plus, a1, button.sw, wire=(BU, 0.75))


def test_the_whole_module_form_and_its_fixed_twin_build_equal_plc_lists() -> None:
    auto, dc, a1 = plc_di_design()
    for number in range(1, 5):
        _button(auto, dc, a1, number)
    fixed, dc2, a2 = plc_di_design()
    for number in range(1, 5):
        _button(fixed, dc2, getattr(a2, f"di_{number}"), number)
    assert _channels(auto) == _channels(fixed)
