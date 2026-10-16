"""A baseline cut by an older fransys is compared under the rules of that release (LS3).

A PE bar with two wired motors is released, then its stored listing is re-cut the way a release
before 0.18.4 wrote it (the bar's screw printed) and its manifest says so. `fr.verify` notes the
moved rule as one INFO; a real change on top of it is an ERROR naming the changed section only.
"""

import hashlib
import json
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import GNYE

from fransys_model.derive import baseline, unit_release
from fransys_model.vocab.tables import units


class _Open(NamedTuple):
    pass


def _bar(revision: int, wired: tuple[str, ...]) -> Any:
    @fr.unit("ls-bar", revision=revision, interface_version=1, date="2026-10-14", text="r", by="AB")
    def bar(u: Any) -> _Open:
        pe1 = u.device("PE1", "DEMO-PEBAR-20").pe
        motors = {n: u.device(n, "DEMO-MOTOR-4KW") for n in ("M1", "M2", "M3")}
        for name in wired:
            u.detail.wire(motors[name].motor["PE"], pe1, wire=(GNYE, 2.5))
        return _Open()

    return bar


def _cabinet(bar: Any) -> Any:
    @fr.unit("ls-cab", revision=1, interface_version=1, date="2026-10-14", text="r", by="AB")
    def cab(u: Any) -> _Open:
        u.add(bar, "B1")
        return _Open()

    return cab


def _build(unit: Any) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    return fr.build(d)


def _plant(folder: Path, result: fr.BuildResult, version: str | None) -> None:
    """Re-cut `folder`'s listing as before 0.18.4 and say `version` in its manifest."""
    model = result.model
    uid = next(i for i in units(model) if unit_release(model, i).name == "ls-bar")
    old = baseline.listing(model, uid, baseline.ListingRules(bar_end_without_screw=False))
    text = baseline.dumps(old)
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


def _released(tmp_path: Path, version: str | None) -> Path:
    into = tmp_path / "baselines"
    result = _build(_bar(1, ("M1", "M2")))
    _plant(fr.release(result, into, unit="ls-bar"), result, version)
    return into


def _codes(findings: Any) -> list[tuple[str, str]]:
    return [(f.code, f.severity.name) for f in findings]


def test_a_moved_rule_is_one_info_and_no_error(tmp_path: Path) -> None:
    into = _released(tmp_path, "0.18.3")
    findings = fr.verify(_build(_bar(1, ("M1", "M2"))), into)
    assert _codes(findings) == [("BASELINE_RULES_MOVED", "INFO")]
    assert "0.18.4" in findings[0].message


def test_a_real_change_beside_a_moved_rule_is_an_error_naming_conductors_only(
    tmp_path: Path,
) -> None:
    into = _released(tmp_path, "0.18.3")
    findings = fr.verify(_build(_bar(1, ("M1", "M3"))), into)
    assert _codes(findings) == [("BASELINE_DIFFERS", "ERROR")]
    assert findings[0].message.endswith("in: conductors")


@pytest.mark.parametrize("version", ["0.9.0", None])
def test_a_baseline_older_than_the_table_or_with_no_version_is_refused(
    tmp_path: Path, version: str | None
) -> None:
    into = _released(tmp_path, version)
    findings = fr.verify(_build(_bar(1, ("M1", "M2"))), into)
    assert _codes(findings) == [("BASELINE_TOO_OLD", "ERROR")]
    assert baseline.OLDEST_VERIFIABLE in findings[0].message


def test_release_over_a_stale_subtree_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    into = _released(tmp_path, "0.18.3")
    bar = _bar(1, ("M1", "M2"))
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(_build(_cabinet(bar)), into, unit="ls-cab")
    assert _codes(raised.value.findings) == [("BASELINE_RULES_MOVED", "ERROR")]
    assert not (into / "ls-cab").exists()


def test_a_new_revision_is_never_refused_by_a_baseline_too_old(tmp_path: Path) -> None:
    """The way out of `BASELINE_TOO_OLD`: release the unit's next revision, then its container."""
    into = _released(tmp_path, "0.9.0")
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(_build(_cabinet(_bar(1, ("M1", "M2")))), into, unit="ls-cab")
    assert [f.code for f in raised.value.findings] == ["BASELINE_TOO_OLD"]
    bar2 = _bar(2, ("M1", "M2"))
    fr.release(_build(bar2), into, unit="ls-bar")
    assert fr.release(_build(_cabinet(bar2)), into, unit="ls-cab").is_dir()
