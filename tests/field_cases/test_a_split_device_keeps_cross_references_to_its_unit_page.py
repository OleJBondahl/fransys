"""Field case: one device whose coil is the unit's boundary and whose wired contact is not.

The engineering shape: a unit holds one relay and hands back only its coil as interface. A
contact pin of the relay is wired to the coil's pin inside the unit. The coil stands on the
parent's sheets and the contact on the unit's, so the parent's cross-reference names the contact
pin on a unit sheet, and no label on a unit sheet names that pin. A layout profile (hiding
unused pins, or a wider column gap) in the unit body or on the design makes the unit and the
design lay out in two runs.

The bug: building raised LayoutError "cross-reference partner ... is on a replaced page its
unit's run lacks" (splice.py `_homed`). A port's home was taken from the labels on the pages its
run owns, so a port named only by a label on a page the splice drops had none.
The rule (model-0192): a partner names the page and column of the run that owns its page; that
run's labels on the pages it drops name its ports too.

Each profile placement builds once, in a module fixture shared by the tests.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import Label, Page, SymbolPlacement, layout_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from pathlib import Path

_PROFILES: dict[str, dict[str, Any]] = {
    "hide": {"hide_unused_pins": True},
    "gap": {"column_gap": 16},
}


class _Interface(NamedTuple):
    k1: fr.Device


def _unit(profile: dict[str, Any] | None) -> Any:
    @fr.unit("demo-split", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: fr.Design) -> _Interface:
        if profile:
            u.layout.profile(**profile)
        k1 = u.device("K1", "DEMO-RLY-2CO-24", interface=("coil",))
        u.detail.wire(k1.co_1["11"], k1.coil["A1"], wire=("RD", 0.75))
        return _Interface(k1)

    return unit


def _build(root: Path, *, design: str | None, body: str | None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    if design:
        d.layout.profile(**_PROFILES[design])
    d.add(_unit(_PROFILES[body] if body else None), "U1")
    (root / "own.md").write_text("# Split\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-split", cover=root / "own.md")
    )


@pytest.fixture(scope="module", params=["hide-design", "hide-body", "gap-design", "gap-body"])
def result(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> fr.BuildResult:
    profile, where = request.param.split("-")
    root = tmp_path_factory.mktemp(request.param)
    return _build(
        root,
        design=profile if where == "design" else None,
        body=profile if where == "body" else None,
    )


def test_the_split_device_cross_references_stay_whole(result: fr.BuildResult) -> None:
    """Each partner end names a page that exists and the column its function stands at there."""
    model = result.model
    pages = layout_of(model, Page)
    columns = {(p.function, p.page): p.x for p in layout_of(model, SymbolPlacement).values()}
    ends = [end for one in layout_of(model, Label).values() for end in one.partners]
    assert ends
    for end in ends:
        assert end.page in pages
        assert columns[ports(model)[end.port].function, end.page] == end.x
