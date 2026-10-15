"""Field case: a `keep_together` set that undoes an `order` hint says so.

The engineering shape: three relay blocks F1, F2, F3 on one sheet. The author orders F2 before
F3, then asks that F1 and F3 stand together.

The bug: `keep_together` runs after the order hints and pulls F3 next to F1, so the drawing reads
F1, F3, F2 and the order hint is undone. No finding said so; the author's hint was lost without
a trace. Fixed by layout-0231 (CL8 note 3): a WARNING, `ORDER_HINT_UNDONE`, names both hints'
groups; `keep_together` still wins, and the fix is to drop one of the two hints.
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.layout import Page, layout_of

_BU = "BU"


class _Cabinet(NamedTuple):
    pass


def _build(cover: Path) -> tuple[fr.BuildResult, dict[str, Any]]:
    handles: dict[str, Any] = {}

    @fr.unit("cab", revision=1, interface_version=1, date="2026-10-14", text="t", by="X")
    def cabinet(c: Any) -> _Cabinet:
        for i in (1, 2, 3):
            with c.function(f"F{i}", f"Relay {i}") as group:
                k = c.device(f"K{i}", "DEMO-RLY-2CO-24")
                feed = c.terminal_strip(f"X{i}", "DEMO-TB-2.5", 2)
                c.detail.wire(feed[1], k.coil["A1"], wire=("BU", 0.75))
                c.detail.wire(k.coil["A2"], feed[2], wire=("BU", 0.75))
            handles[f"F{i}"] = group
        c.layout.order(handles["F2"], handles["F3"])
        c.layout.keep_together(handles["F1"], handles["F3"])
        return _Cabinet()

    d = fr.design("demo_parts")
    d.add(cabinet, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover)
    return fr.build(d, doc), handles


@pytest.fixture(scope="module")
def built_and_handles(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[fr.BuildResult, dict[str, Any]]:
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Top\n", encoding="utf-8")
    return _build(cover)


def _order(built: fr.BuildResult, handles: dict[str, Any]) -> list[str]:
    names = {h.id: n for n, h in handles.items()}
    pages = sorted(layout_of(built.model, Page).values(), key=lambda p: (p.drawing_set, p.number))
    return [names[g.group] for p in pages for g in p.groups if g.group in names]


def test_the_three_blocks_are_drawn(built_and_handles: Any) -> None:
    built, handles = built_and_handles
    assert sorted(_order(built, handles)) == ["F1", "F2", "F3"]


def test_an_order_hint_undone_by_keep_together_is_reported(built_and_handles: Any) -> None:
    built, handles = built_and_handles
    undone = [f for f in built.findings if f.code == "ORDER_HINT_UNDONE"]
    assert [f.severity.name for f in undone] == ["WARNING"]
    assert set(undone[0].subjects) >= {handles[n].id for n in ("F1", "F2", "F3")}
    assert len(undone[0].subjects) == len(set(undone[0].subjects))
    assert "drop one of the two hints" in undone[0].message
    assert _order(built, handles) == ["F1", "F3", "F2"]
