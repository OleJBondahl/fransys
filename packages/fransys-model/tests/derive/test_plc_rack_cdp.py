"""`rack_modules_for_cdp` keeps channel-bearing modules, counts them per mpn, and gives each channel its CDP kind and nr."""

import pytest
from rack_builders import build_racks

from fransys_model.derive import cdp_kind, rack_modules_for_cdp
from fransys_model.derive.cdp_name import cdp_name
from fransys_model.vocab.enums import SignalType


def test_only_modules_with_channels_are_kept_in_rack_order_with_an_ordinal_per_mpn():
    racks = build_racks()
    found = rack_modules_for_cdp(racks.model, racks.rack)
    assert [entry.module.module for entry in found] == list(racks.modules_in_rack_order)
    assert [entry.ordinal for entry in found] == [0, 1]
    assert racks.coupler not in {entry.module.module for entry in found}


def test_the_ordinal_restarts_in_another_rack():
    racks = build_racks()
    (only,) = rack_modules_for_cdp(racks.model, racks.first_rack)
    assert only.module.module == racks.first_rack_module
    assert only.ordinal == 0


def test_a_module_of_one_kind_names_it_and_its_channels_count_from_zero():
    racks = build_racks()
    found = rack_modules_for_cdp(racks.model, racks.rack)
    assert {e.cdp_kind for e in found} == {"DI"}
    assert [[(c.cdp_kind, c.nr) for c in e.channels] for e in found][1] == [("DI", 0), ("DI", 1)]


@pytest.mark.parametrize(
    ("signal", "kind"),
    [
        (SignalType.DI, "DI"),
        (SignalType.DO, "DO"),
        (SignalType.RELAY, "DO"),
        (SignalType.AI_CURRENT, "AI"),
        (SignalType.AI_VOLTAGE, "AI"),
        (SignalType.RTD, "AI"),
        (SignalType.AO_CURRENT, "AO"),
        (SignalType.AO_VOLTAGE, "AO"),
    ],
)
def test_the_cdp_kind_is_the_form_and_the_direction_of_the_signal(signal, kind):
    assert cdp_kind(signal) == kind


@pytest.mark.parametrize(
    ("text", "name"),
    [("Door", "Door"), ("Door!", "Door"), ("B-1", "B_1"), ("a  b", "a_b"), ("__x__", "x"), ("1st", "N_1st"), ("Ä1", "N_1"), ("!!!", ""), ("", "")],
)
def test_the_cdp_name_keeps_letters_digits_and_underscores_only(text, name):
    assert cdp_name(text) == name
