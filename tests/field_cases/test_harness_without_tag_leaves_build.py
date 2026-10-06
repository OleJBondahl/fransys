"""Field case: a two-plug harness authored as a part-less container item with a cable child,
through `d.harness(name=...)` with no tag.

The bug: `is_harness` is structural (H2, decision model-0043): any container with a `cable`-
faceted child reads as a harness, whether or not it carries a tag. The tag
is optional on `d.harness`; an untagged one has no designation, and one of
its own children (here, a plug) needs that ancestor's label to render its own. F1 (facade spec)
says `fr.build` raises only `FreezeError` and `MergeConflict`; any other exception leaving
`build` is a bug. `fransys_model/derive/designation.py`'s `_ancestor_label` still raises a
bare `SchemaError` ("harness ... has no designation: give it a tag") for this container, but
nothing between there and `fr.build` reaches it any more: a `HARNESS_WITHOUT_TAG` validator
(decision model-0107) reports the same condition as an `ERROR` `Finding` first, calling H2's own
`is_harness` predicate, and `fr.write` raises `BuildErrors` on it, never a bare `SchemaError`.

Found in the review of the consumer guide, reproduced 2026-09-26. Fixed by decision model-0107.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_CODE = "HARNESS_WITHOUT_TAG"


def _build(tmp_path: Path) -> fr.BuildResult:
    """A unit holding one two-ended cable between two plugs, its container item authored with
    no tag: structurally a harness (a `cable`-faceted child), but with no label of its own.
    """

    @fr.unit(
        "unit",
        revision=1,
        interface_version=1,
        date="2026-09-26",
        text="First issue",
        by="XX",
    )
    def assembly(u: fr.Design) -> _Open:
        u.location("L0", "Harness 0")
        with u.function("HAR", "Harness"):
            container = u.harness(name="w0", place="L0")
            near = u.device("P0A", _PLUG, parent=container, place="L0")
            far = u.device("P0B", _PLUG, parent=container, place="L0")
            cable = u.cable("W0", _CABLE, parent=container, name="w0c", place="L0")
            cable.core(1, near[1], far[1])
        return _Open()

    d = fr.design("demo_parts")
    d.add(assembly, "UNIT")
    cover = tmp_path / "unit.md"
    cover.write_text("# Harness\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "unit", cover=cover)
    return fr.build(d, doc)


def test_harness_without_tag_leaves_build(tmp_path: Path) -> None:
    """`HARNESS_WITHOUT_TAG` names the container; `fr.write` raises `BuildErrors`, never a
    bare `SchemaError` (model-0107).
    """
    result = _build(tmp_path)
    (finding,) = [f for f in result.findings if f.code == _CODE]
    assert finding.severity is Severity.ERROR
    for part in ("w0", "tag"):
        assert part in finding.message
    with pytest.raises(fr.BuildErrors) as raised:
        fr.write(result, tmp_path / "out")
    assert _CODE in {f.code for f in raised.value.findings}
