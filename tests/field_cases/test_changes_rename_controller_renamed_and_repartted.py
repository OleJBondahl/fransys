"""Field case: a device is given a `place=` and another part in the same release.

The engineering shape: as the placed-controller case, but the revision that adds `place="CSN"`
to the housing `X1` also swaps its part (a female housing for a male one, same pins).

The bug: the rename printed as a removal plus an addition, so the part swap vanished into it:
no row said the part had changed.

The rule (decision model-0300, CHANGES-RENAME): the item is matched by key, so the list holds one
`renamed` row and, under the new designation, the real change as today's `changed` row (`mpn`).
"""

import csv
import io
from typing import TYPE_CHECKING

import fransys as fr
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
    d.detail.wire(x1[1], x2[1], wire=(BK, 0.5))
    return fr.build(d)


def _rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]


def test_a_renamed_and_repartted_device_gives_renamed_and_mpn_rows(tmp_path: Path) -> None:
    """One `renamed` row, and the `mpn` change under the new designation."""
    fr.release(_build(1, place=None, part="DEMO-HSG-4F"), tmp_path)
    rows = _rows(fr.release(_build(2, place="CSN", part="DEMO-HSG-4M"), tmp_path))
    (renamed,) = _of(rows, "items", "renamed")
    assert (renamed["subject"], renamed["before"], renamed["after"]) == (
        "+CSN-X1",
        "-X1",
        "+CSN-X1",
    )
    (changed,) = [r for r in _of(rows, "items", "changed") if r["field"] == "mpn"]
    assert (changed["subject"], changed["before"], changed["after"]) == (
        "+CSN-X1",
        "DEMO-HSG-4F",
        "DEMO-HSG-4M",
    )
    assert _of(rows, "items", "added") == []
    assert _of(rows, "items", "removed") == []
