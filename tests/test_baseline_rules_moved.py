"""A baseline cut by an older fransys is compared under the rules of that release (LS3).

A PE strip with two wired motors is released, then its manifest is made to say an older fransys wrote it.
`fr.verify` compares it under the rules of that release.
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
        pe = u.terminal_strip("X1", "DEMO-TB-PE-2.5")
        motors = {n: u.device(n, "DEMO-MOTOR-4KW") for n in ("M1", "M2", "M3")}
        for i, name in enumerate(wired, 1):
            u.series(motors[name].motor["PE"], pe[i], wire=(GNYE, 2.5))
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
    """Say `version` in `folder`'s manifest."""
    model = result.model
    uid = next(i for i in units(model) if unit_release(model, i).name == "ls-bar")
    old = baseline.listing(model, uid, baseline.ListingRules())
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


def _moved_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every demo row the old holder rule changes is unprintable (`rows_unchecked`), so say `rules_moved` by hand."""
    status = baseline.ListingStatus("rules_moved", moved_in="0.18.2")
    monkeypatch.setattr(baseline, "listing_status", lambda *_a, **_k: status)


def test_a_moved_rule_is_one_info_and_no_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    into = _released(tmp_path, "0.18.1")
    _moved_rule(monkeypatch)
    findings = fr.verify(_build(_bar(1, ("M1", "M2"))), into)
    assert _codes(findings) == [("BASELINE_RULES_MOVED_NOTE", "INFO")]
    assert "0.18.2" in findings[0].message


def test_release_over_a_stale_subtree_is_refused_and_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    into = _released(tmp_path, "0.18.1")
    _moved_rule(monkeypatch)
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.release(_build(_cabinet(_bar(1, ("M1", "M2")))), into, unit="ls-cab")
    assert _codes(raised.value.findings) == [("BASELINE_RULES_MOVED_REFUSED", "ERROR")]
    assert not (into / "ls-cab").exists()


def test_a_real_change_beside_a_moved_rule_is_an_error_naming_conductors_only(
    tmp_path: Path,
) -> None:
    into = _released(tmp_path, "0.18.3")
    findings = fr.verify(_build(_bar(1, ("M1", "M3"))), into)
    assert _codes(findings) == [("BASELINE_DIFFERS", "ERROR")]
    assert findings[0].message.endswith("in: conductors")


@pytest.mark.parametrize("version", ["0.9.0", None])
def test_a_baseline_older_than_the_table_or_with_no_version_is_refused(tmp_path: Path, version: str | None) -> None:
    into = _released(tmp_path, version)
    findings = fr.verify(_build(_bar(1, ("M1", "M2"))), into)
    assert _codes(findings) == [("BASELINE_TOO_OLD", "ERROR")]
    assert "cut a new revision with fr.release; the old revision stays as released" in findings[0].message


def test_a_new_revision_is_never_refused_by_a_baseline_too_old(tmp_path: Path) -> None:
    """The way out of `BASELINE_TOO_OLD`: release the unit's next revision, then its container."""
    into = _released(tmp_path, "0.9.0")
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.release(_build(_cabinet(_bar(1, ("M1", "M2")))), into, unit="ls-cab")
    assert [f.code for f in raised.value.findings] == ["BASELINE_TOO_OLD"]
    bar2 = _bar(2, ("M1", "M2"))
    fr.release(_build(bar2), into, unit="ls-bar")
    assert fr.release(_build(_cabinet(bar2)), into, unit="ls-cab").is_dir()
