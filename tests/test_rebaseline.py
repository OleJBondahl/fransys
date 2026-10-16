"""`fr.rebaseline` re-cuts stored listings under today's rules and leaves every export (LS4).

The tree is `stale_releases.stale_tree`: board, cabinet and plant, the cabinet and the plant cut by
an older fransys. A call leaves `fr.verify` clean, changes nothing but `listing.json` and
`manifest.json`, refuses a real change without writing, and a second call writes nothing.
"""

import dataclasses
import json
import shutil
from typing import Any
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys._release_reader import stored_fransys_version
from stale_releases import (
    build_plant,
    cut_old,
    old_listing,
    release_all,
    stale_tree,
    tree_hashes,
)

_RECUT = ("baseline/listing.json", "baseline/manifest.json")


@pytest.fixture(scope="module")
def template(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Any]:
    root = tmp_path_factory.mktemp("stale")
    result, _ = stale_tree(root / "baselines")
    return root / "baselines", result


@pytest.fixture
def tree(template: tuple[Path, Any], tmp_path: Path) -> tuple[Path, Any]:
    into = tmp_path / "baselines"
    shutil.copytree(template[0], into)
    return into, template[1]


def _manifest(folder: Path) -> dict[str, Any]:
    return json.loads((folder / "baseline" / "manifest.json").read_text(encoding="utf-8"))


def test_verify_is_clean_after_and_notes_the_stale_baseline_before(tree: tuple[Path, Any]) -> None:
    into, result = tree
    assert [f.code for f in fr.verify(result, into)] == ["BASELINE_RULES_MOVED"]
    rewritten = fr.rebaseline(result, into)
    assert [p.parent.name for p in rewritten] == ["lg-cabinet", "lg-plant"]
    assert fr.verify(result, into) == ()


def test_every_file_but_the_listing_and_the_manifest_keeps_its_bytes(
    tree: tuple[Path, Any],
) -> None:
    into, result = tree
    before = tree_hashes(into)
    fr.rebaseline(result, into)
    after = tree_hashes(into)
    assert after.keys() == before.keys()
    moved = {name for name in before if before[name] != after[name]}
    assert {name.split("/", 2)[2] for name in moved} == set(_RECUT)
    assert {name.split("/")[0] for name in moved} == {"lg-cabinet", "lg-plant"}
    assert any("/data/" in name for name in before)  # the exports are in the tree compared


def test_the_manifest_names_the_old_values(tree: tuple[Path, Any]) -> None:
    into, result = tree
    folder = next(into.glob("lg-cabinet/*"))
    old = _manifest(folder)["listing_digest"]
    fr.rebaseline(result, into)
    data = _manifest(folder)
    (record,) = data["rebaselined"]
    assert record["listing_digest"] == old
    assert record["listing_digest"] != data["listing_digest"]
    assert (record["listing_version"], record["fransys"], record["reason"]) == (
        1,
        "0.18.3",
        "rules",
    )
    assert (record["unit"], record["unchecked_rows"]) == (None, 0)
    assert stored_fransys_version(folder) == record["cut_by"]


def test_a_parent_pin_takes_the_childs_new_digest_and_names_the_child(
    tree: tuple[Path, Any],
) -> None:
    into, result = tree
    fr.rebaseline(result, into)
    cabinet = _manifest(next(into.glob("lg-cabinet/*")))
    plant = _manifest(next(into.glob("lg-plant/*")))
    pin = next(row for row in plant["nested"] if row["name"] == "lg-cabinet")
    assert pin["listing_digest"] == cabinet["listing_digest"]
    (record,) = plant["rebaselined"]
    assert (record["reason"], record["unit"]) == ("nested", "lg-cabinet")
    assert record["listing_digest"] == plant["listing_digest"]


def test_rows_left_out_are_counted_in_the_record(tmp_path: Path) -> None:
    result, _ = stale_tree(tmp_path, "0.18.1")
    fr.rebaseline(result, tmp_path)
    (record,) = _manifest(next(tmp_path.glob("lg-cabinet/*")))["rebaselined"]
    assert record["unchecked_rows"] == 3
    assert fr.verify(result, tmp_path) == ()


def test_a_real_change_raises_and_writes_nothing(tmp_path: Path) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    cut_old(folders["lg-plant"], result, "lg-plant", "0.18.3")
    listing = old_listing(result, "lg-cabinet")
    rows = tuple(
        dataclasses.replace(c, colour="BU") if c.a == "-M1:PE" else c for c in listing.conductors
    )
    changed = dataclasses.replace(listing, conductors=rows)
    cut_old(folders["lg-cabinet"], result, "lg-cabinet", "0.18.3", changed)
    before = tree_hashes(tmp_path)
    with pytest.raises(fr.BuildErrors) as raised:
        fr.rebaseline(result, tmp_path)
    assert [f.code for f in raised.value.findings] == ["BASELINE_DIFFERS"]
    assert tree_hashes(tmp_path) == before


def test_a_second_call_writes_nothing(tree: tuple[Path, Any]) -> None:
    into, result = tree
    assert fr.rebaseline(result, into) != ()
    after = tree_hashes(into)
    assert fr.rebaseline(result, into) == ()
    assert tree_hashes(into) == after


def test_a_unit_rewrites_itself_and_the_units_below_only(tree: tuple[Path, Any]) -> None:
    into, result = tree
    rewritten = fr.rebaseline(result, into, unit="lg-cabinet")
    assert [p.parent.name for p in rewritten] == ["lg-cabinet"]
    assert "rebaselined" not in _manifest(next(into.glob("lg-plant/*")))


def test_a_tree_the_current_fransys_cut_is_not_touched(tmp_path: Path) -> None:
    result = build_plant()
    release_all(result, tmp_path)
    before = tree_hashes(tmp_path)
    assert fr.rebaseline(result, tmp_path) == ()
    assert tree_hashes(tmp_path) == before


def test_the_manifest_keeps_every_other_field_and_its_canonical_form(
    tree: tuple[Path, Any],
) -> None:
    into, result = tree
    folder = next(into.glob("lg-cabinet/*"))
    before = _manifest(folder)
    fr.rebaseline(result, into)
    after = _manifest(folder)
    for key in ("model_digest", "unit", "history", "packages", "part_libraries", "warnings"):
        assert after[key] == before[key]
    others = [r for r in after["files"] if r["path"] != "baseline/listing.json"]
    assert others == [r for r in before["files"] if r["path"] != "baseline/listing.json"]
    text = (folder / "baseline" / "manifest.json").read_text(encoding="utf-8")
    assert (
        text == json.dumps(after, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
