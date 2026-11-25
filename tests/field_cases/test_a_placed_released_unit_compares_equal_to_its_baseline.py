"""Field case: a released unit nested in a parent that places it (place=) or names supplies on its terminal strip.
The bug: the parent's placement node and supply nets moved the unit's compared rows, so `fr.verify` gave BASELINE_DIFFERS.
Fixed by model-0476 (R2635-R2638): the nested comparison keeps what the unit authored; the standalone bytes do not move."""

import hashlib
from typing import NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import RD


class _Io(NamedTuple):
    feed: fr.TerminalStrip


@fr.unit("demo-leaf", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _leaf(d: fr.Design) -> _Io:
    x1, s1 = d.device("X1", "DEMO-CONN-2P", interface=True, unused=True), d.device("S1", "DEMO-CONN-2P", place="DOOR")
    d.series(x1.x1.pins[0], s1.x1.pins[0], wire=(RD, 0.5))
    return _Io(d.terminal_strip("X2", "DEMO-TB-2.5", 4, interface=True))


@pytest.mark.parametrize(("place", "supply"), [("BR", False), (None, False), (None, True), ("BR", True)])
def test_a_placed_released_unit_compares_equal_to_its_baseline(place: str | None, tmp_path, *, supply: bool) -> None:
    """The standalone listing keeps its bytes, and the nested unit compares equal to it, placed or supplied or not."""
    alone = fr.design("demo_parts")
    alone.add(_leaf, "U1")
    fr.release(fr.build(alone, unit_document("demo-leaf"), releases=tmp_path), tmp_path, unit="demo-leaf")
    listing = (tmp_path / "demo-leaf/1.1/baseline/listing.json").read_bytes()
    assert hashlib.sha256(listing).hexdigest() == "d908b8dbb5c32f29e55bb10282be2b85853fcffb67e7f4c840bc59f8744f9c75"
    d = fr.design("demo_parts")
    feed = d.add(_leaf, "U1", place=place).feed
    if supply:
        d.ac_supply("400V", 230, feed[1], feed[2], feed[3], n=feed[4], names=("L1", "L2", "L3", "N"))
    assert "BASELINE_DIFFERS" not in [f.code for f in fr.verify(fr.build(d, unit_document("demo-leaf"), releases=tmp_path), tmp_path)]
