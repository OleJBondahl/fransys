"""No facade code opens a file under a release folder outside the one reader."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "fransys"
READS = frozenset(
    {"read_text", "read_bytes", "open", "iterdir", "glob", "rglob", "is_file", "is_dir"}
)
# `documents.py` reads a cover, notes and logo; `pipeline.py`'s `out_dir` globs are the write side.
# `settings.py` reads our packaged TOML files and a consumer's settings file, not a release folder.
# `_settings_library.py` reads a consumer's font files, named in the settings file.
# `_help_names.py` reads the packaged guide pages (`help KEY`), not a release folder.
ALLOWED = {
    "_release_reader.py": READS,
    "documents.py": READS,
    "pipeline.py": {"glob", "is_file"},
    "settings.py": {"read_text"},
    "_settings_library.py": {"read_bytes", "is_file"},
    "_help_names.py": {"iterdir", "read_text"},
}


def _reads(source: str) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in READS
    }


def _offenders(files: dict[str, str]) -> dict[str, set[str]]:
    found = {name: _reads(text) - ALLOWED.get(name, set()) for name, text in files.items()}
    return {name: reads for name, reads in found.items() if reads}


def test_only_the_reader_reads_release_folders():
    files = {p.name: p.read_text(encoding="utf-8") for p in SRC.glob("*.py")}
    assert _offenders(files) == {}


def test_the_check_can_fail():
    assert _offenders({"pipeline.py": "p.read_text()"}) == {"pipeline.py": {"read_text"}}
    assert _offenders({"_release_files.py": "p.iterdir()"}) == {"_release_files.py": {"iterdir"}}
