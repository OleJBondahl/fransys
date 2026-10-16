"""Field case: the old release holds a version-1 listing, which has no item keys.

The engineering shape: as the placed-controller case, but release 1 was cut by a fransys whose
listing (version 1) names no authoring key. The stored listing is rewritten here as that file
looked: `listing_version` 1 and every `key` field gone (a manifest digest kept in step).

The bug: nothing told the engineer that the rename could not be followed, so the removed and
added rows looked like a real replacement.

The rule (decision model-0300, CHANGES-RENAME, CR3): with a keyless side the diff matches by
printed text as before (removed plus added, no `renamed` row) and adds one INFO finding,
`CHANGES_BY_NAME`: "renames are not followed: the listing of <release> has no item keys".
"""

import csv
import hashlib
import io
import json
from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None, releases: Path | None = None) -> fr.BuildResult:
    """Controller `K1` wired to connector `X1`; `place` is the only thing that moves."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-4", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    k1 = d.device("K1", "DEMO-CTRL-8", place=place)
    x1 = d.device("X1", "DEMO-CONN-2P")
    d.detail.wire(k1.X1["1"], x1["1"], wire=(BK, 0.5))
    return fr.build(d, releases=releases)


def _strip_keys(value: object) -> object:
    if isinstance(value, dict):
        return {k: _strip_keys(v) for k, v in value.items() if k != "key"}
    if isinstance(value, list):
        return [_strip_keys(v) for v in value]
    return value


def _make_version_1(release: Path) -> None:
    """Rewrite `release`'s listing as version 1 without keys; keep the manifest digest true."""
    path = release / "baseline" / "listing.json"
    data = _strip_keys(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(data, dict)
    data["listing_version"] = 1
    text = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    manifest_path = release / "baseline" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["listing_digest"] = digest
    for row in manifest["files"]:
        if row["path"].endswith("listing.json"):
            row["sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]


def test_a_version_1_old_listing_gives_removed_added_and_one_info_finding(tmp_path: Path) -> None:
    """Today's rows, no `renamed` row, and exactly one INFO `CHANGES_BY_NAME` finding."""
    first = fr.release(_build(1, place=None), tmp_path)
    _make_version_1(first)
    new = _build(2, place="CSN", releases=tmp_path)
    rows = _rows(fr.release(new, tmp_path))
    assert [r["subject"] for r in _of(rows, "items", "removed")] == ["-K1"]
    assert [r["subject"] for r in _of(rows, "items", "added")] == ["+CSN-K1"]
    assert _of(rows, "items", "renamed") == []
    found = [f for f in (*fr.check(new), *fr.verify(new, tmp_path)) if f.code == "CHANGES_BY_NAME"]
    assert len(found) == 1
    assert str(found[0].severity).lower().endswith("info")
    assert (
        "renames are not followed: the listing of CR-4 1.1 has no item keys; fr.rebaseline"
        in found[0].message
    )
