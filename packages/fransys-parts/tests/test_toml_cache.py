"""`_toml.parse` caches on the file's text (decision 0122): same text hits, new text re-parses."""

from typing import TYPE_CHECKING

from fransys_parts import _toml

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, text: str) -> Path:
    path = root / "p.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_second_parse_of_the_same_text_is_a_cache_hit(tmp_path: Path) -> None:
    path = _write(tmp_path, '[part]\nmpn = "A-1"\n')
    _toml.parse(path, relative_to=tmp_path)
    hits = _toml._parse_text.cache_info().hits
    again = _toml.parse(path, relative_to=tmp_path)
    assert _toml._parse_text.cache_info().hits == hits + 1
    assert again.data == {"part": {"mpn": "A-1"}}


def test_changed_text_in_the_same_file_is_parsed_again(tmp_path: Path) -> None:
    path = _write(tmp_path, '[part]\nmpn = "A-1"\n')
    first = _toml.parse(path, relative_to=tmp_path)
    path.write_text('[part]\nmpn = "B-2"\n\n[[function]]\nname = "f"\n', encoding="utf-8")
    second = _toml.parse(path, relative_to=tmp_path)
    assert first.data == {"part": {"mpn": "A-1"}}
    assert second.data == {"part": {"mpn": "B-2"}, "function": [{"name": "f"}]}
    assert second.origins != first.origins


def test_a_caller_editing_the_result_cannot_reach_the_cache(tmp_path: Path) -> None:
    path = _write(tmp_path, '[part]\nmpn = "A-1"\n')
    first = _toml.parse(path, relative_to=tmp_path)
    assert first.data is not None
    first.data["part"]["mpn"] = "EDITED"
    first.origins[("x",)] = 99
    again = _toml.parse(path, relative_to=tmp_path)
    assert again.data == {"part": {"mpn": "A-1"}}
    assert ("x",) not in again.origins
