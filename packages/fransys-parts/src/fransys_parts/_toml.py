"""Read one part-file TOML file: parse it, and find the line of every table header.

`tomllib` gives no line numbers (spec P6): this module scans a file's text once for its
own table headers (`[part]`, `[[function]]`, `[function.connector]`, `[[supply]]` and so
on) and records the line each one starts on, so the rest of the package can attribute one
line to every record without writing a TOML parser. It is a header scan, not a TOML
parser: a header inside a multi-line string would be miscounted, so the contract forbids a
line break inside any string. That check (`MULTILINE_STRING`) is made on the parsed values
after a successful parse, never by searching the file text for quote marks, which would
misfire on a comment holding triple quotes, or a literal triple-quote mark in an ordinary string.
"""

import re
import tomllib
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Finding, Severity

if TYPE_CHECKING:
    from pathlib import Path

_ARRAY_HEADER = re.compile(r"^\[\[([A-Za-z_][A-Za-z0-9_]*)\]\]$")
_TABLE_HEADER = re.compile(r"^\[([A-Za-z_][A-Za-z0-9_.]*)\]$")

# A nested facet header such as `[function.connector]` is exactly this many dotted segments.
_NESTED_HEADER_SEGMENTS = 2

type TablePath = tuple[str | int, ...]
type Origins = dict[TablePath, int]
type Table = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParsedFile:
    """One TOML file under the library root: `data` (None if unreadable), header lines, findings.

    A bad file only adds findings; it never raises.
    """

    path: str
    data: dict[str, Any] | None
    origins: dict[TablePath, int]
    findings: tuple[Finding, ...]


def location(path: str, line: int, text: str) -> str:
    """`"<path>:<line>: <text>"`, the message form every finding in this package uses."""
    return f"{path}:{line}: {text}"


def finding(
    code: str, path: str, line: int, text: str, *, severity: Severity = Severity.ERROR
) -> Finding:
    """One `Finding` with no subjects; the message carries `path` and `line` (spec P6)."""
    return Finding(code=code, severity=severity, subjects=(), message=location(path, line, text))


def parse(file_path: Path, *, relative_to: Path) -> ParsedFile:
    """Read and parse `file_path`; never raises. The parse is cached on the file's text (0122)."""
    rel = file_path.relative_to(relative_to).as_posix()
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        text_finding = finding("FILE_UNREADABLE", rel, 1, str(exc))
        return ParsedFile(path=rel, data=None, origins={}, findings=(text_finding,))
    cached = _parse_text(text, rel)
    # The cache keeps its own copy: a caller that edits `data` or `origins` cannot reach it.
    return replace(cached, data=_copy(cached.data), origins=dict(cached.origins))


@lru_cache(maxsize=512)
def _parse_text(text: str, rel: str) -> ParsedFile:
    try:
        data = tomllib.loads(text, parse_float=Decimal)
    except tomllib.TOMLDecodeError as exc:
        return ParsedFile(
            path=rel, data=None, origins={}, findings=(finding("TOML_INVALID", rel, 1, str(exc)),)
        )
    origins = _scan_origins(text)
    findings = value_findings(data, rel, origins)
    return ParsedFile(path=rel, data=data, origins=origins, findings=tuple(findings))


def _copy(value: Any) -> Any:  # noqa: ANN401 - a TOML value is a dict, list, str, int, bool or Decimal
    if type(value) is dict:
        return {key: _copy(item) for key, item in value.items()}
    if type(value) is list:
        return [_copy(item) for item in value]
    return value


def value_findings(data: dict[str, Any], rel: str, origins: dict[TablePath, int]) -> list[Finding]:
    """`FLOAT_FORBIDDEN` and `MULTILINE_STRING` over every parsed value (spec P6, P8)."""
    findings: list[Finding] = []
    for key, value in data.items():
        if type(value) is list and (key, 0) in origins:
            for index, entry in enumerate(value):
                _walk_value(entry, rel, origins, (key, index), findings)
        else:
            _walk_value(value, rel, origins, (key,), findings)
    return findings


def _walk_value(
    value: object, rel: str, origins: dict[TablePath, int], path: TablePath, findings: list[Finding]
) -> None:
    if type(value) is str:
        if "\n" in value:
            text = "a string value may not contain a line break"
            findings.append(finding("MULTILINE_STRING", rel, origins.get(path, 1), text))
        return
    if type(value) is Decimal:
        text = "a bare TOML float; write it as a quoted string"
        findings.append(finding("FLOAT_FORBIDDEN", rel, origins.get(path, 1), text))
        return
    if type(value) is dict:
        for raw_key, sub_value in value.items():
            key = raw_key if type(raw_key) is str else str(raw_key)
            child_path = (*path, key) if (*path, key) in origins else path
            _walk_value(sub_value, rel, origins, child_path, findings)
        return
    if type(value) is list:
        for item in value:
            _walk_value(item, rel, origins, path, findings)


def _scan_origins(text: str) -> dict[TablePath, int]:
    """Every table header's line, keyed by the table path it opens."""
    origins: dict[TablePath, int] = {}
    counters: dict[str, int] = {}
    current_function = -1
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line.startswith("["):
            continue
        array_match = _ARRAY_HEADER.match(line)
        if array_match is not None:
            name = array_match.group(1)
            index = counters.get(name, 0)
            counters[name] = index + 1
            origins[(name, index)] = line_no
            if name == "function":
                current_function = index
            continue
        table_match = _TABLE_HEADER.match(line)
        if table_match is None:
            continue
        segments = tuple(table_match.group(1).split("."))
        if (
            len(segments) == _NESTED_HEADER_SEGMENTS
            and segments[0] == "function"
            and current_function >= 0
        ):
            origins[("function", current_function, segments[1])] = line_no
        elif len(segments) == 1:
            origins[segments] = line_no
    return origins
