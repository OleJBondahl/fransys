"""Field case: a tag change is a new identity, beside a place change that is a rename.
The bug: both printed as a removal plus an addition, with nothing to tell a rename from a new part.
Fixed by model-0300 (CHANGES-RENAME CR4): a place change is one renamed row; a tag change stays removed and added."""

from typing import TYPE_CHECKING

import fransys as fr
from _changes_rows import changes_rows, rows_of

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None, tag: str) -> fr.BuildResult:
    """Connectors `K1` (placed by `place`) and one tagged `tag`."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-3", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    d.device("K1", "DEMO-CONN-2P", place=place)
    d.device(tag, "DEMO-CONN-2P")
    return fr.build(d)


def test_a_tag_change_is_a_removal_plus_an_addition_and_no_rename(tmp_path: Path) -> None:
    """`K1` is renamed; `K2` to `K3` is removed plus added; no other renamed row."""
    fr.release(_build(1, place=None, tag="K2"), tmp_path)
    rows = changes_rows(fr.release(_build(2, place="CSN", tag="K3"), tmp_path))
    (renamed,) = rows_of(rows, "items", "renamed")
    assert renamed["subject"] == "+CSN-K1"
    assert [r["subject"] for r in rows_of(rows, "items", "removed")] == ["-K2"]
    assert [r["subject"] for r in rows_of(rows, "items", "added")] == ["-K3"]
