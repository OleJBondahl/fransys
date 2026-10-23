"""Field case: a relay on no net is left off the page, and a finding names it (R324, R335).

The engineering shape: three relays in one cabinet, the coils of K1 and K2 wired together and K3
wired to nothing (its contacts are unwired too). The bug: layout dropped K3's symbols without a
word. The rule: a thing left off a page is a Finding that names it; leaving an unwired symbol
off is an el convention
(FUNCTION_NOT_WIRED, decision NO-SILENT-DROP).
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _build(cover: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("C1", "Cabinet")
    with d.function("R", "Relays"):
        k1, k2, _k3 = (d.device(f"K{i}", "DEMO-RLY-2CO-24", place="C1") for i in (1, 2, 3))
    d.detail.wire(k1.coil["A1"], k2.coil["A1"], wire=("WH", 0.75))
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover))


@pytest.mark.rule("NO-SILENT-DROP")
def test_the_unwired_coil_is_named_and_the_wired_coils_are_not(tmp_path: Path) -> None:
    found = [f for f in fr.check(_build(tmp_path / "cover.md")) if f.code == "FUNCTION_NOT_WIRED"]
    named = {f.message.split()[3] for f in found}
    assert "K3:coil" in named
    assert not {"K1:coil", "K2:coil"} & named
    assert all(f.severity is fr.Severity.WARNING for f in found)
