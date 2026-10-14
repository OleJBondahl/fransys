"""A channel wired to two or more kind-matched requests is contested (PLC-CONTESTED, model-0211).

One `PLC_CHANNEL_CONTESTED` per channel; the requests bind nothing and skip the free queue. Invented
data. The helpers come from the two sibling modules named below.
"""

from plant import Plant
from test_plc_allocation_units_model import Site, _bound, _site
from test_plc_allocation_wired_model import _request

from fransys_model.derive.numbering_pins import name_findings
from fransys_model.derive.passes._plc_contested import PLC_CHANNEL_CONTESTED
from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.vocab.enums import SignalType


def test_two_requests_wired_to_one_channel_give_one_finding_and_no_binding() -> None:
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, _ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    port = plant.port(ch1, "1")
    first = _request(plant, "dev-1", unit, to=port)
    second = _request(plant, "dev-2", unit, to=port)
    model, findings = allocate_plc(plant.model())
    assert _bound(model) == {}
    (found,) = findings
    assert found.code == PLC_CHANNEL_CONTESTED
    assert found.subjects[0] == ch1
    assert set(found.subjects[1:]) == {first, second}
    (named,) = name_findings(model, findings)
    assert "-U1:1" in named.message
    assert "B-dev-1" in named.message
    assert "B-dev-2" in named.message
    assert "one channel reads one signal: keep one request, or wire each request" in named.message


def test_two_requests_on_two_channels_bind_as_wired() -> None:
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    first = _request(plant, "dev-1", unit, to=plant.port(ch2, "1"))
    second = _request(plant, "dev-2", unit, to=plant.port(ch1, "1"))
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {first: ch2, second: ch1}


def test_a_wrong_kind_request_beside_a_kind_matched_one_still_yields() -> None:
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    (ch1,) = _site(plant, Site("rack-u", "mod-u", "U1", 1, unit))
    port = plant.port(ch1, "1")
    wrong = _request(plant, "dev-do", unit, to=port, signal=SignalType.DO)
    right = _request(plant, "dev-di", unit, to=port)
    model, findings = allocate_plc(plant.model())
    assert _bound(model) == {right: ch1}
    assert {f.code for f in findings} == {PLC_REQUEST_UNSERVABLE}
    assert findings[0].subjects[1] == wrong


def test_two_wrong_kind_requests_are_not_contested_and_go_to_the_free_queue() -> None:
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    ch1, ch2 = _site(plant, Site("rack-u", "mod-u", "U1", 2, unit))
    port = plant.port(ch1, "1")
    first = _request(plant, "dev-1", unit, to=port, signal=SignalType.DO)
    second = _request(plant, "dev-2", unit, to=port, signal=SignalType.DO)
    _model, findings = allocate_plc(plant.model())
    assert PLC_CHANNEL_CONTESTED not in {f.code for f in findings}
    assert {f.subjects[1] for f in findings} == {first, second}
    assert ch2 not in {s for f in findings for s in f.subjects}
