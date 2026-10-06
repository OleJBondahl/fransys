"""The committed `releases/` folders still match the model (`fr.verify`).

A released revision is frozen: if the design changes, the unit's revision is raised and released
again, never edited in place. The twin test shows the check can fail.
"""

from pathlib import Path

import fransys as fr

RELEASES = Path(__file__).resolve().parent.parent / "releases"


def test_both_units_are_released() -> None:
    assert (RELEASES / "relay-interface-board" / "1.3" / "baseline" / "listing.json").is_file()
    assert (RELEASES / "pump-cabinet" / "1.6" / "baseline" / "listing.json").is_file()


def test_verify_finds_no_difference_from_the_releases(built: tuple) -> None:
    result, _out_dir, _intermediates = built
    assert fr.verify(result, RELEASES) == ()


def test_verify_fails_when_a_released_listing_changes(built: tuple, tmp_path: Path) -> None:
    """Can-fail proof: the same check reports a finding against an edited copy of a release."""
    result, _out_dir, _intermediates = built
    copy = tmp_path / "releases"
    for source in RELEASES.rglob("*"):
        if source.is_file():
            target = copy / source.relative_to(RELEASES)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    listing = copy / "pump-cabinet" / "1.6" / "baseline" / "listing.json"
    text = listing.read_text(encoding="utf-8")
    assert "LC1D09BD" in text
    listing.write_text(text.replace("LC1D09BD", "LC1D09BX", 1), encoding="utf-8")
    assert fr.verify(result, copy)
