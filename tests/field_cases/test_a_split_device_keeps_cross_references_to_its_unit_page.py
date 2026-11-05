"""Field case: a unit hands up only the coil of its one relay as interface, while a contact pin of that relay is wired inside the unit.
The bug: build raised LayoutError (partner on a replaced page), since a port's home came only from labels on pages its run owns.
Fixed by model-0192, a partner names the page and column of the run that owns its page, and that run's labels name its ports too."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages

from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

_PROFILES: dict[str, dict[str, Any]] = {
    "hide": {"hide_unused_pins": True},
}


class _Interface(NamedTuple):
    k1: fr.Device


def _unit(profile: dict[str, Any] | None) -> Any:
    @fr.unit("demo-split", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: fr.Design) -> _Interface:
        if profile:
            u.layout.profile(**profile)
        k1 = u.device("K1", "DEMO-RLY-2CO-24", interface=("coil",))
        u.series(k1.co_1["11"], k1.coil["A1"], wire=("RD", 0.75))
        u.series(k1.co_2["21"], k1.coil["A2"], wire=("RD", 0.75))
        return _Interface(k1)

    return unit


def _build(root: Path, *, design: str | None, body: str | None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    if design:
        d.layout.profile(**_PROFILES[design])
    d.add(_unit(_PROFILES[body] if body else None), "U1")
    (root / "own.md").write_text("# Split\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-split", cover=root / "own.md"))


@pytest.fixture(scope="module", params=["hide-design", "hide-body"])
def result(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    profile, where = request.param.split("-")
    root = tmp_path_factory.mktemp(request.param)
    return _build(
        root,
        design=profile if where == "design" else None,
        body=profile if where == "body" else None,
    )


def test_the_split_device_cross_references_stay_whole(result: fr.BuildResult) -> None:
    """Each cross-reference names a page that exists and the column its function stands at there."""
    pages = layout_of(result.model, Page)
    drawn = drawn_pages(result.model)
    assert set(drawn) <= set(pages)
    ends = [s for d in drawn.values() for s in d.symbols if s.key == "reference-marker"]
    assert ends
    for end in ends:
        assert dict(end.slots)["ref"]
        assert any(s.x == end.x for d in drawn.values() for s in d.symbols if s is not end)
