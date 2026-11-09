"""The worked example through the real parts loader (model-0088).

A battery string (`DEMO-STRING-864V`, 186 A continuous), a partial-range fuse (`DEMO-FUSE-ABAT`,
400 A) and a DC contactor pole (`DEMO-CONTACTOR-DC`, 150 A) on each pole, ending at an external
"""

import shutil
from pathlib import Path

import fransys_parts
from fransys_author.design import Design
from root_library import freeze
lazy from fransys_author.handles import Item

from fransys_model.checks.ratings_current import (
    RATING_CURRENT_BELOW_BRANCH,
    check_ratings_current,
)
from fransys_model.kernel import Model, merge

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo-parts" / "demo_parts"
_CONTACTOR = ("parts/contactor-dc.toml", 'current = [{ nom = "150 A", at = ["DC"] }]')
_FUSE = ("parts/fuse-abat.toml", 'current = [{ nom = "400 A", at = ["DC"] }]')
_PARTIAL = ("parts/fuse-abat.toml", 'breaking_capacity = [{ min = "4000 A" }]\n')


def _library(tmp_path: Path, *edits: tuple[tuple[str, str], str]) -> Path:
    """A copy of the demo library with each `((file, text), replacement)` applied."""
    root = tmp_path / "lib"
    shutil.copytree(DEMO, root, ignore=shutil.ignore_patterns("__pycache__", "*.py"))
    for (name, text), replacement in edits:
        path = root / name
        content = path.read_text()
        assert text in content
        path.write_text(content.replace(text, replacement))
    return root


def _string(root: Path) -> tuple[Model, dict[str, Item]]:
    """The string, and on each pole a fuse and a contactor pole, ending at an external terminal."""
    library = fransys_parts.load_path(root)
    d = Design(library)
    wire = d.wiring(colour="BK", gauge="1.5")
    d.supply("HV", current="dc", rails={"DC+": ("985.5", None), "DC-": ("0", None)})
    string = d.item("DEMO-STRING-864V", name="s1")
    items: dict[str, Item] = {}
    for pole, port in (("plus", "+"), ("minus", "-")):
        fuse = d.item("DEMO-FUSE-ABAT", name=f"f-{pole}")
        contactor = d.item("DEMO-CONTACTOR-DC", name=f"k-{pole}")
        d.net(f"DC{port}", string[port], cls="power", potential=f"DC{port}")
        wire(string[port], fuse["1"])
        wire(fuse["2"], contactor["1"])
        # The string ends at the external switchboard's terminal: the outside closes its loop.
        terminal = d.strip(f"t-{pole}", external=True).terminal("DEMO-TB-2.5")
        wire(contactor["2"], terminal.inner)
        items[f"f-{pole}"], items[f"k-{pole}"] = fuse, contactor
    return freeze(merge(library, d.draft())), items


def _findings(tmp_path: Path, *edits: tuple[tuple[str, str], str]):
    model, items = _string(_library(tmp_path, *edits))
    return model, items, check_ratings_current(model)


def test_a_contactor_rated_150_a_on_each_pole_gives_a_finding_per_pole(tmp_path) -> None:
    _, items, found = _findings(tmp_path)
    assert {f.subjects for f in found} == {
        (items["k-plus"].fn("pole").id,),
        (items["k-minus"].fn("pole").id,),
    }
    for finding in found:
        assert finding.code == RATING_CURRENT_BELOW_BRANCH
        assert "rated 150 A DC" in finding.message
        assert "below its branch's 186 A DC set by the source of function ⟨function:" in (finding.message)


def test_a_contactor_rated_200_a_passes(tmp_path) -> None:
    assert _findings(tmp_path, (_CONTACTOR, 'current = [{ nom = "200 A", at = ["DC"] }]'))[2] == ()


def test_a_full_range_fuse_of_400_a_leaves_the_bound_at_186_a(tmp_path) -> None:
    """The spec's remark: without a `min` breaking figure the fuse is full-range, and min(186,
    400) is still 186 A."""
    found = _findings(tmp_path, (_PARTIAL, ""))[2]
    assert len(found) == 2
    assert all("below its branch's 186 A DC set by the source" in f.message for f in found)


def test_a_partial_range_fuse_of_100_a_bounds_nothing_and_is_itself_below_the_bound(
    tmp_path,
) -> None:
    """The 150 A contactor still fires (bound 186 A, not 100 A), and so do the two 100 A fuses."""
    _, items, found = _findings(tmp_path, (_FUSE, 'current = [{ nom = "100 A", at = ["DC"] }]'))
    assert {f.subjects for f in found} == {
        (items[name].fn(function).id,)
        for name, function in (
            ("k-plus", "pole"),
            ("k-minus", "pole"),
            ("f-plus", "element"),
            ("f-minus", "element"),
        )
    }
    assert all("below its branch's 186 A DC set by the source" in f.message for f in found)
