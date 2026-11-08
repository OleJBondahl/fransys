"""Field case: a supply terminal chains three phases through a row of starters wider than a page, so the cut falls inside the fan.
KI-495 (R1553, part 0): every piece joins by a reference pair, so no connection is undrawn and a copy has an end per page beyond the hub's."""

import contextvars
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, BN, GY

from fransys_layout.core import cut
from fransys_model.kernel import id_namespace

if TYPE_CHECKING:
    from pathlib import Path

_PH = (BN, BK, GY)
_STARTERS = 40


class _Io(NamedTuple):
    L1: fr.Run
    L2: fr.Run
    L3: fr.Run


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet")
def _cabinet(u: Any) -> _Io:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    l1, l2, l3 = (x1.run(k, 1) for k in ("L1", "L2", "L3"))
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5")
    loads = [x3.run(k, _STARTERS) for k in ("U", "V", "W")]
    ends = [run[1].inner for run in (l1, l2, l3)]  # a terminal point takes one conductor (R1266): each phase chains from starter to starter
    for n in range(1, _STARTERS + 1):
        ct = u.device(f"Q{n}1", "DEMO-CTR-3P-24")
        for i in range(3):
            u.series(ends[i], ct.main[str(2 * i + 1)], wire=(_PH[i], 1.5))
            u.series(ct.main[str(2 * i + 2)], loads[i][n].inner, wire=(_PH[i], 1.5))
            ends[i] = ct.main[str(2 * i + 1)]
    return _Io(l1, l2, l3)


def _built(tmp_path: Path, copied: list[tuple[int, int]], patch: pytest.MonkeyPatch) -> Any:
    """Build the cabinet; `copied` gets (ends, pages beyond the hub's) for each copy reference planned."""
    plan = cut.copies

    def spy(flow: Any, where: Any, copyable: Any) -> list[Any]:
        refs = plan(flow, where, copyable)
        for ref in refs:
            fan = next(f for f in flow.fans if ref.net in f.nets)
            attached = (*fan.drivers, *fan.legs)
            pages = {where[n] for a in attached if (n := a.column or a.pin.sym) in where}
            hub = next(a.column for a in attached if a.pin.sym == fan.hub)
            copied.append((len(ref.ends), len(pages - {where[hub or ""]})))
        return refs

    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cabinet, "U1", place=None)
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", external=True)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
    for core, (outside, inside) in enumerate(zip((x0.run(k, 1) for k in ("L1", "L2", "L3")), cab, strict=True), start=1):
        w1.core(core, outside[1], inside[1])
    cover = tmp_path / "cover.md"
    cover.write_text("# Fan\n", encoding="utf-8")
    patch.setattr(cut, "copies", spy)
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


@pytest.mark.rule("WHERE-WIRED")
@pytest.mark.parametrize("salt", ["-", "a", "b", "c", "d", "e"])
def test_a_split_fan_has_a_copy_end_on_every_page_beyond_the_hubs_and_no_connection_undrawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, salt: str
) -> None:
    """KI-495: the fan reaches 3 pages; its copy has 2 ends and CONNECTION_NOT_DRAWN is 0 at every salt.

    MARKER_UNPLACED is 0 (KI-604 closed); ANNEX_UNPLACED is 0 too (STRIP-TAG-ONCE: a run's tag is one annex).
    """
    copied: list[tuple[int, int]] = []

    def salted() -> list[str]:
        if salt != "-":
            id_namespace(salt)  # a context of its own: the salt never leaks into another test
        findings = _built(tmp_path, copied, monkeypatch).findings
        assert not [f.message for f in findings if f.severity.name == "ERROR"], "the drawing must be made for the check to mean anything"
        return [f.code for f in findings if f.code in {"CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END", "MARKER_UNPLACED", "ANNEX_UNPLACED"}]

    assert contextvars.copy_context().run(salted) == []
    assert copied
    assert all(ends == pages >= 2 for ends, pages in copied)  # the cut fell inside the fan
