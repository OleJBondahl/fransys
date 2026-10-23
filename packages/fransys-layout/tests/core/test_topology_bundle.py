"""Tests for the bundle errors of core/topology_split.py: a bundle cannot lose a member."""

from __future__ import annotations

import pytest

from fransys_layout.core import CoreError, PinRef
from fransys_layout.core.topology_split import BundleError, check_bundles, split_fans
from fransys_layout.core.values import Attach, Fan


def _box(sym: str, pin: str) -> Attach:
    return Attach(None, 0, 0, PinRef(sym, pin))


def _bundle(drivers: tuple[Attach, ...], legs: tuple[Attach, ...]) -> Fan:
    return Fan("f:b", ("n1", "n2", "n3"), drivers, legs, None, 3, "above")


NET_OF = {PinRef("M", "U"): "n1", PinRef("M", "V"): "n2", PinRef("M", "W"): "n3"}


def test_a_bundle_with_a_driver_and_a_leg_on_one_box_names_the_bundle_node_and_nets() -> None:
    fan = _bundle((_box("M", "U"), _box("M", "W")), (_box("M", "V"), _box("P", "1")))
    with pytest.raises(BundleError, match=r"bundle f:b \(nets n1, n2, n3\).*box:M") as e:
        check_bundles((), [fan])
    assert isinstance(e.value, CoreError)


def test_a_bundle_whose_driver_and_leg_stand_apart_passes() -> None:
    fan = _bundle((_box("M", "U"), _box("M", "W")), (_box("P", "1"),))
    check_bundles((), [fan])


def test_a_plain_fan_with_a_driver_and_a_leg_on_one_node_is_not_a_bundle_error() -> None:
    fan = Fan("f:p", ("n1",), (_box("M", "U"),), (_box("M", "V"),), None, 1, "above")
    check_bundles((), [fan])


def test_cutting_a_net_out_of_a_bundle_names_the_bundle_and_the_net() -> None:
    fan = _bundle((_box("M", "U"), _box("M", "W")), (_box("M", "V"), _box("P", "1")))
    with pytest.raises(BundleError, match=r"cut net n2 out of bundle f:b"):
        split_fans([fan], [], {"n2"}, NET_OF)


def test_cutting_a_net_out_of_a_plain_fan_still_splits_it() -> None:
    fan = Fan(
        "f:p", ("n1", "n2"), (_box("M", "U"),), (_box("P", "1"), _box("M", "V")), None, 1, "above"
    )
    kept, links = split_fans([fan], [], {"n2"}, NET_OF | {PinRef("P", "1"): "n1"})
    assert [c.net for c in links] == ["n2"]
    assert kept[0].nets == ("n1",)
