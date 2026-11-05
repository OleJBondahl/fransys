"""Field case: a revision gives housing X1 a `place=` and also swaps its part for a same-pin part in the same release.
The bug: the rename printed as a removal plus an addition, so the part swap vanished into it and no row said the part had changed.
Fixed by model-0300 (CHANGES-RENAME), the item is matched by key: one `renamed` row, and a `changed` row (`mpn`) for the swap."""

from typing import TYPE_CHECKING

import fransys as fr
from _changes_rows import changes_rows, rows_of
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None, part: str) -> fr.BuildResult:
    """Housing `X1` of `part` wired to connector `X2`."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-2", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    contacts = "DEMO-CRIMP-F" if part == "DEMO-HSG-4F" else "DEMO-CRIMP-M"
    x1 = d.device("X1", part, place=place, contacts=contacts)
    x2 = d.device("X2", "DEMO-CONN-2P")
    d.series(x1[1], x2[1], wire=(BK, 0.5))
    return fr.build(d)


def test_a_renamed_and_repartted_device_gives_renamed_and_mpn_rows(tmp_path: Path) -> None:
    """One `renamed` row, and the `mpn` change under the new designation."""
    fr.release(_build(1, place=None, part="DEMO-HSG-4F"), tmp_path)
    rows = changes_rows(fr.release(_build(2, place="CSN", part="DEMO-HSG-4M"), tmp_path))
    (renamed,) = rows_of(rows, "items", "renamed")
    assert (renamed["subject"], renamed["before"], renamed["after"]) == (
        "+CSN-X1",
        "-X1",
        "+CSN-X1",
    )
    (changed,) = [r for r in rows_of(rows, "items", "changed") if r["field"] == "mpn"]
    assert (changed["subject"], changed["before"], changed["after"]) == (
        "+CSN-X1",
        "DEMO-HSG-4F",
        "DEMO-HSG-4M",
    )
    assert rows_of(rows, "items", "added") == []
    assert rows_of(rows, "items", "removed") == []
