"""`plan_rebaseline` reads and compares and writes nothing (LS4, root-0214).

The tree is `stale_releases.stale_tree`: a board, a cabinet nesting it and a plant nesting the
cabinet, the cabinet and the plant cut by an older fransys. The plan orders children first.
"""

import dataclasses
from typing import Any
lazy from pathlib import Path

from fransys._rebaseline import Plan, plan_rebaseline
from stale_releases import (
    build_plant,
    cut_old,
    old_listing,
    release_all,
    stale_tree,
    tree_hashes,
    unit_id,
)
lazy import fransys as fr


def _plan(result: fr.BuildResult, into: Path, name: str | None = None) -> Any:
    unit = None if name is None else unit_id(result, name)
    return plan_rebaseline(result.model, into, unit)


def _names(plan: Any) -> list[str]:
    return [rewrite.folder.parent.name for rewrite in plan.rewrites]


def test_a_tree_cut_by_this_fransys_plans_nothing(tmp_path: Path) -> None:
    result = build_plant()
    release_all(result, tmp_path)
    assert _plan(result, tmp_path) == Plan((), ())


def test_a_moved_rule_is_one_rewrite_and_children_come_before_parents(tmp_path: Path) -> None:
    result, _ = stale_tree(tmp_path)
    plan = _plan(result, tmp_path)
    assert plan.findings == ()
    assert _names(plan) == ["lg-cabinet", "lg-plant"]
    cabinet, plant = plan.rewrites
    assert (cabinet.listing_text is None, plant.listing_text is None) == (False, True)
    assert [pin.key[0] for pin in plant.pins] == ["lg-cabinet"]
    assert (cabinet.old_fransys, cabinet.unchecked) == ("0.18.3", 0)


def test_rows_the_old_holder_rule_cannot_print_are_counted(tmp_path: Path) -> None:
    result, _ = stale_tree(tmp_path, "0.18.1")
    cabinet = _plan(result, tmp_path).rewrites[0]
    assert (cabinet.old_fransys, cabinet.unchecked) == ("0.18.1", 3)


def test_a_unit_scopes_the_plan_to_itself_and_the_units_below(tmp_path: Path) -> None:
    result, _ = stale_tree(tmp_path)
    assert _names(_plan(result, tmp_path, "lg-cabinet")) == ["lg-cabinet"]
    assert _names(_plan(result, tmp_path, "lg-board")) == []
    assert _names(_plan(result, tmp_path, "lg-plant")) == ["lg-cabinet", "lg-plant"]


def test_a_unit_with_no_stored_baseline_is_skipped(tmp_path: Path) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    cut_old(folders["lg-cabinet"], result, "lg-cabinet", "0.18.3")
    for path in sorted(folders["lg-plant"].rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    folders["lg-plant"].rmdir()
    assert _names(_plan(result, tmp_path)) == ["lg-cabinet"]


def test_a_real_change_is_baseline_differs_naming_the_section_and_no_rewrite(
    tmp_path: Path,
) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    listing = old_listing(result, "lg-cabinet")
    rows = tuple(
        dataclasses.replace(c, colour="BU") if c.a == "-M1:PE" else c for c in listing.conductors
    )
    cut_old(
        folders["lg-cabinet"],
        result,
        "lg-cabinet",
        "0.18.3",
        dataclasses.replace(listing, conductors=rows),
    )
    before = tree_hashes(tmp_path)
    plan = _plan(result, tmp_path)
    assert plan.rewrites == ()
    assert [(f.code, f.severity.name) for f in plan.findings] == [("BASELINE_DIFFERS", "ERROR")]
    assert plan.findings[0].message.endswith("in: conductors")
    assert tree_hashes(tmp_path) == before


def test_a_baseline_older_than_the_table_is_the_refusal(tmp_path: Path) -> None:
    result, _ = stale_tree(tmp_path, "0.9.0")
    plan = _plan(result, tmp_path)
    assert plan.rewrites == ()
    assert [f.code for f in plan.findings] == ["BASELINE_TOO_OLD", "BASELINE_TOO_OLD"]


def test_a_release_file_not_as_released_refuses_the_plan(tmp_path: Path) -> None:
    result, folders = stale_tree(tmp_path)
    (folders["lg-board"] / "baseline" / "model.json").write_text("{}", encoding="utf-8")
    plan = _plan(result, tmp_path)
    assert plan.rewrites == ()
    assert [f.code for f in plan.findings] == ["RELEASE_FILE_CHANGED"]


def test_a_pin_already_at_the_new_digest_moves_nothing(tmp_path: Path) -> None:
    result = build_plant()
    folders = release_all(result, tmp_path)
    cut_old(folders["lg-cabinet"], result, "lg-cabinet", "0.18.3")
    assert _names(_plan(result, tmp_path)) == ["lg-cabinet"]
