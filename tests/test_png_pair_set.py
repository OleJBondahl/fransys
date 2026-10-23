"""The completeness check of the P7.3 PNG pair set can fail: a missing picture is named."""

from _png_pair_set import CASES, ROLES, missing_pairs


def _full(directory) -> None:
    for case in CASES:
        for role in ROLES:
            for side in ("before", "after"):
                (directory / f"{case}-{role}-{side}.png").write_bytes(b"png")


def test_a_complete_pair_set_has_nothing_missing(tmp_path) -> None:
    _full(tmp_path)
    assert missing_pairs(tmp_path) == []


def test_a_missing_core_picture_is_named(tmp_path) -> None:
    _full(tmp_path)
    (tmp_path / "own-schematic-after.png").unlink()
    assert missing_pairs(tmp_path) == ["own-schematic-after.png"]


def test_a_named_reason_covers_a_missing_picture(tmp_path) -> None:
    _full(tmp_path)
    (tmp_path / "w04-schematic-after.png").unlink()
    assert missing_pairs(tmp_path, {"w04-schematic-after.png": "unit document"}) == []


def test_an_empty_directory_misses_every_picture(tmp_path) -> None:
    assert len(missing_pairs(tmp_path)) == len(CASES) * len(ROLES) * 2
