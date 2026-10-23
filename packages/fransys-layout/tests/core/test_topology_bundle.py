"""Tests for the bundle errors of core/topology_split.py: a bundle cannot lose a member."""

from __future__ import annotations

import pytest

from fransys_layout.core import CoreError, PinRef
from fransys_layout.core.topology_split import BundleError, check_bundles, split_fans
from fransys_layout.core.values import Attach, Fan

NET_OF = {PinRef("M", "U"): "n1", PinRef("M", "V"): "n2", PinRef("M", "W"): "n3"}


def _box(sym: str, pin: str) -> Attach:
    return Attach(None, 0, 0, PinRef(sym, pin), net=NET_OF.get(PinRef(sym, pin), "n1"))


def _bundle(drivers: tuple[Attach, ...], legs: tuple[Attach, ...]) -> Fan:
    return Fan("f:b", ("n1", "n2", "n3"), drivers, legs, None, 3, "above")


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
        split_fans([fan], [], {"n2"})


def test_cutting_a_net_out_of_a_plain_fan_still_splits_it() -> None:
    fan = Fan(
        "f:p", ("n1", "n2"), (_box("M", "U"),), (_box("P", "1"), _box("M", "V")), None, 1, "above"
    )
    kept, links = split_fans([fan], [], {"n2"})
    assert [c.net for c in links] == ["n2"]
    assert kept[0].nets == ("n1",)


def test_an_attach_carries_its_net_and_cannot_be_built_without_one() -> None:
    assert Attach(None, 0, 0, PinRef("T", "n"), 0, net="n2").net == "n2"
    with pytest.raises(TypeError):
        Attach(None, 0, 0, PinRef("T", "n"))  # ty: ignore[missing-argument] - proves the net is required
