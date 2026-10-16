"""Release trees cut as an older fransys wrote them, for the rules-moved tests (LS3, LS4).

`cut_old` re-cuts one released unit's `listing.json` and manifest the way a release before a rule
moved wrote them. The demo cabinet (`listing_golden_cases`) holds a contact block, a PE bar and a
nested board; `lg-plant` nests the cabinet, so one tree carries both rules and three levels.
"""

import hashlib
import json
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from listing_golden_cases import _cabinet

from fransys_model.derive import baseline, unit_release
from fransys_model.vocab.tables import units

OLD_BAR = baseline.ListingRules(bar_end_without_screw=False)
NAMES = ("lg-board", "lg-cabinet", "lg-plant")


class _Open(NamedTuple):
    pass


@fr.unit("lg-plant", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _plant(u: Any) -> _Open:
    u.add(_cabinet, "K1")
    return _Open()


def build_plant() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_plant, "P1")
    return fr.build(d)


def release_all(result: fr.BuildResult, into: Path) -> dict[str, Path]:
    """Release the board, the cabinet, then the plant; the folders by unit name."""
    return {name: fr.release(result, into, unit=name) for name in NAMES}


def unit_id(result: fr.BuildResult, name: str) -> Any:
    model = result.model
    return next(i for i in units(model) if unit_release(model, i).name == name)


def old_listing(result: fr.BuildResult, name: str) -> Any:
    """`name`'s listing cut as a release before 0.18.4 wrote it (the holder rule is today's)."""
    return baseline.listing(result.model, unit_id(result, name), OLD_BAR)


def cut_old(
    folder: Path, result: fr.BuildResult, name: str, version: str | None, listing: Any = None
) -> str:
    """Rewrite `folder`'s listing (default `old_listing`) and say `version`; the new digest."""
    text = baseline.dumps(listing or old_listing(result, name))
    (folder / "baseline" / "listing.json").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    path = folder / "baseline" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["listing_digest"] = digest
    for row in manifest["files"]:
        if row["path"].endswith("listing.json"):
            row["sha256"] = digest
    manifest["packages"] = [p for p in manifest["packages"] if p["name"] != "fransys"]
    if version is not None:
        manifest["packages"].append({"name": "fransys", "version": version})
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return digest


def age_pin(folder: Path, child: str, digest: str) -> None:
    """Set `folder`'s manifest pin of release `child` to `digest`, as an older parent cut it."""
    path = folder / "baseline" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for row in manifest["nested"]:
        if row["name"] == child:
            row["listing_digest"] = digest
    path.write_text(json.dumps(manifest), encoding="utf-8")


def stale_tree(into: Path, version: str = "0.18.3") -> tuple[fr.BuildResult, dict[str, Path]]:
    """Release all three; the cabinet and the plant cut as `version` wrote them, pins to match."""
    result = build_plant()
    folders = release_all(result, into)
    digest = cut_old(folders["lg-cabinet"], result, "lg-cabinet", version)
    cut_old(folders["lg-plant"], result, "lg-plant", version)
    age_pin(folders["lg-plant"], "lg-cabinet", digest)
    return result, folders


def tree_hashes(root: Path) -> dict[str, str]:
    """Every file below `root` with its sha256."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
