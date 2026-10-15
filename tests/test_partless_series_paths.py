"""Every series entry that resolves a function template refuses a part-less device cleanly.

A part-less device has no template: before author-0054 each of these raised `KeyError: None`.
"""

from types import SimpleNamespace

import fransys as fr
import pytest


def _design() -> SimpleNamespace:
    d = fr.design("demo_parts")
    xa = d.terminal_strip("XA", "DEMO-TB-2.5")
    supply = d.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
    qa = d.device("QA", "DEMO-MCB-3P")
    ext = d.device("E1", None, external=True, pins=("U", "V", "W"))
    return SimpleNamespace(d=d, supply=supply, qa=qa, ext=ext)


def _first(b: SimpleNamespace) -> None:
    b.d.series(b.ext, b.qa.element, wire=2.5)


def _middle_device(b: SimpleNamespace) -> None:
    b.d.series(b.supply, b.ext, b.qa.element, wire=2.5)


def _middle_function(b: SimpleNamespace) -> None:
    b.d.series(b.supply, b.ext.box, b.qa.element, wire=2.5)


def _in_a_parallel(b: SimpleNamespace) -> None:
    b.d.series(b.supply, b.d.parallel(b.qa.element, b.ext), b.qa.element, wire=2.5)


def _in_a_pole_group(b: SimpleNamespace) -> None:
    b.d.series(b.supply, b.d.poles(b.ext.box), b.qa.element, wire=2.5)


def _last_as_a_pole_group(b: SimpleNamespace) -> None:
    b.d.series(b.supply, b.qa.element, b.d.poles(b.ext.box), wire=2.5)


def _as_a_supply(b: SimpleNamespace) -> None:
    b.d.dc_supply("S", b.ext)


def _as_a_carrier(b: SimpleNamespace) -> None:
    b.d.device("K9", "DEMO-RLY-2CO-24", mounted_on=b.ext)


@pytest.mark.parametrize(
    "walk",
    [
        _first,
        _middle_device,
        _middle_function,
        _in_a_parallel,
        _in_a_pole_group,
        _last_as_a_pole_group,
        _as_a_supply,
        _as_a_carrier,
    ],
)
def test_no_path_to_a_template_raises_a_key_error(walk) -> None:
    with pytest.raises(fr.AuthorError):
        walk(_design())
