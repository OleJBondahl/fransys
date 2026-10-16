"""Field case: a tag change is a new identity, beside a place change that is a rename.

The engineering shape: two connectors in one system. In the next revision `K1` gets
`place="CSN"` and `K2` is retagged `K3`. The authoring key is (scope prefix, tag), so the first
keeps its key and the second does not.

The bug: both printed as a removal plus an addition, with nothing to tell a rename from a new part.

The rule (decision model-0300, CHANGES-RENAME, CR4): `K1` is one `renamed` row; `K2` -> `K3`
stays one removed row plus one added row and gives no `renamed` row, as the engineer chose it.
"""

import csv
import io
from typing import TYPE_CHECKING

import fransys as fr

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


def _rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]


def test_a_tag_change_is_a_removal_plus_an_addition_and_no_rename(tmp_path: Path) -> None:
    """`K1` is renamed; `K2` to `K3` is removed plus added; no other renamed row."""
    fr.release(_build(1, place=None, tag="K2"), tmp_path)
    rows = _rows(fr.release(_build(2, place="CSN", tag="K3"), tmp_path))
    (renamed,) = _of(rows, "items", "renamed")
    assert renamed["subject"] == "+CSN-K1"
    assert [r["subject"] for r in _of(rows, "items", "removed")] == ["-K2"]
    assert [r["subject"] for r in _of(rows, "items", "added")] == ["-K3"]
