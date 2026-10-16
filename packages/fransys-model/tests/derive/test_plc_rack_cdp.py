"""`rack_modules_for_cdp` keeps channel-bearing modules, counts them per mpn, and `name_stem`."""

from rack_builders import build_racks

from fransys_model.derive import plc_rack_modules, rack_modules_for_cdp
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


def test_a_module_of_one_signal_type_names_it():
    racks = build_racks()
    assert {e.single_signal for e in rack_modules_for_cdp(racks.model, racks.rack)} == {
        SignalType.DI
    }


def test_a_spare_channel_stem_is_the_module_designation_and_its_index():
    racks = build_racks()
    module = plc_rack_modules(racks.model, racks.rack)[1]
    assert [channel.name_stem for channel in module.channels] == [
        f"{module.designation}_0",
        f"{module.designation}_1",
    ]
