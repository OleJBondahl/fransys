"""S20 M8 (amended after 4b6d's 8e stop): one box names several pins only when they are
neighbours with one destination.

A row whose destinations alternate (a changeover's four throws to X02, X01, X02, X01 in pin
order) gets one box per pin: a run of the same far end that another destination's pin stands
inside would overlap that pin's box. A cable's neighbouring stubs, and a run of neighbouring
terminals of one strip, keep their one shared box.

Can-fail: a grouping by cable and far end alone (no cut at another destination's pin) puts pins
1 and 3 in one box over pin 2, and the first test fails.
"""

from samples import PROFILE, SHEET, built, connection, drawn, hid, placed, standing

from fransys_layout.stages.references.off_stubs import _off_markers
from fransys_layout.stages.references.types import MarkerScene, OffStubs
from fransys_layout.stages.types import StubText

_XS = {1: 64, 2: 96, 3: 128, 4: 160}


def _markers(goes: dict[int, tuple[str, str]]):
    """Functions 1..4 side by side in one column; each leaves its `n2` port to `(cable, far)`."""
    scene = MarkerScene(
        tuple(placed(n, x=_XS[n], y=160, name="a") for n in goes),
        tuple(drawn(n) for n in goes),
        SHEET,
        PROFILE,
    )
    off = OffStubs(
        tuple(connection(n, n, 90 + n) for n in goes),
        off_texts={
            hid("port", n * 10 + 2): [StubText(cable=cable, far=far, port=f":{n}")]
            for n, (cable, far) in goes.items()
        },
    )
    return scene, off, built(scene, _off_markers(scene, standing(scene, off)))


def test_alternating_destinations_get_one_box_per_pin() -> None:
    far = {1: "+F-X02", 2: "+F-X01", 3: "+F-X02", 4: "+F-X01"}
    scene, off, markers = _markers({n: ("", f) for n, f in far.items()})
    assert {d.run for d in _off_markers(scene, standing(scene, off))} == {None}
    texts = {m.port: m.text for m in markers}
    assert texts == {hid("port", n * 10 + 2): f"→ {f}:{n}" for n, f in far.items()}
    assert len({m.box for m in markers}) == 4  # four boxes, none shared


def test_a_cables_neighbouring_stubs_keep_their_shared_box() -> None:
    _, _, markers = _markers({n: ("-W3", "+F-X02" if n < 3 else "+F-X01") for n in _XS})
    texts = {m.port: m.text for m in markers}
    assert texts[hid("port", 12)] == texts[hid("port", 22)] == "-W3 → +F-X02:1 2"
    assert texts[hid("port", 32)] == texts[hid("port", 42)] == "-W3 → +F-X01:3 4"
    assert len({m.box for m in markers}) == 2


def test_a_run_of_neighbouring_terminals_of_one_strip_keeps_its_shared_box() -> None:
    _, _, markers = _markers(dict.fromkeys(_XS, ("", "+F-X02")))
    assert {m.text for m in markers} == {"→ +F-X02:1 2 3 4"}
    (box,) = {m.box for m in markers}
    assert box.x < 64
    assert box.x + box.width > 160
