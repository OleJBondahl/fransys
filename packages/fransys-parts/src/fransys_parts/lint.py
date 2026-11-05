"""Lint a part library without building a model.

Every finding has the one severity of its code. Codes are
listed next to the check that raises them, and every finding's message carries its file
and line (`_toml.finding`): `lint()` hands back bare findings with no model to resolve
an id's origin through, so the location lives in the text instead.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

from fransys_model.vocab import DESIGNATION_SCHEME
lazy from fransys_model.kernel import Finding

from . import _cable_pairs, _connection, _fields, _lint_function, _ratings, _toml

if TYPE_CHECKING:
    from ._toml import ParsedFile

SUPPORTED_SCHEMAS: frozenset[int] = frozenset({2})

_OLD_SCHEMA = 1
_FILE_NAME = re.compile(r"^[a-z0-9_-]+$")
_CLASS_CODE = re.compile(DESIGNATION_SCHEME.class_code)

_PART_FILE_TABLES = frozenset({"part", "function", "supply", "footprint", "cable_product", "pcb", "rating", "block", "connection"})


def lint(root: Path) -> tuple[Finding, ...]:
    """Check every part file under `root` against the part-file contract.

    Never raises for a malformed library, a missing `library.toml` included
    (`LIBRARY_FILE_MISSING`). Part files are read in name order, so the result does not
    depend on directory listing order (spec acceptance).
    """
    root = Path(root)
    library_file = root / "library.toml"
    if not library_file.is_file():
        return (_toml.finding("LIBRARY_FILE_MISSING", "library.toml", 1, "no library.toml under this root"),)

    findings, library_schema = _lint_library(library_file, root)
    parts_dir = root / "parts"
    part_files = sorted(parts_dir.glob("*.toml")) if parts_dir.is_dir() else []
    seen_parts: dict[tuple[str, str], str] = {}
    for file_path in part_files:
        findings.extend(_lint_part_file(file_path, root, library_schema, seen_parts))
    return tuple(findings)


def _lint_library(library_file: Path, root: Path) -> tuple[list[Finding], int | None]:
    """The findings of `library.toml` and its schema, if it names one."""
    library = _toml.parse(library_file, relative_to=root)
    findings: list[Finding] = list(library.findings)
    if library.data is None:
        return findings, None
    findings.extend(_fields.check_fields(library.data, _fields.LIBRARY_FIELDS, path=library.path, line=1, table_name="library.toml"))
    raw_schema = library.data.get("schema")
    if type(raw_schema) is not int:
        return findings, None
    if raw_schema not in SUPPORTED_SCHEMAS:
        findings.append(_schema_unsupported(library.path, 1, raw_schema))
    return findings, raw_schema


def _lint_part_file(file_path: Path, root: Path, library_schema: int | None, seen_parts: dict[tuple[str, str], str]) -> list[Finding]:
    findings: list[Finding] = []
    rel_name = file_path.relative_to(root).as_posix()
    if _FILE_NAME.fullmatch(file_path.stem) is None:
        findings.append(
            _toml.finding(
                "FILE_NAME",
                rel_name,
                1,
                "a part file name should be lowercase with hyphens, digits and underscores",
            )
        )
    parsed = _toml.parse(file_path, relative_to=root)
    findings.extend(parsed.findings)
    if parsed.data is not None:
        findings.extend(_check_part_file(parsed, library_schema, seen_parts))
    return findings


def _schema_unsupported(path: str, line: int, value: int) -> Finding:
    if value == _OLD_SCHEMA:
        return _toml.finding("PART_SCHEMA_OLD", path, line, "schema 1 is old")
    supported = ", ".join(str(v) for v in sorted(SUPPORTED_SCHEMAS))
    text = f"schema {value} is not supported (supported: {supported})"
    return _toml.finding("SCHEMA_UNSUPPORTED", path, line, text)


def _line(origins: _toml.Origins, path_key: _toml.TablePath, default: int = 1) -> int:
    return origins.get(path_key, default)


def _check_part_file(parsed: ParsedFile, library_schema: int | None, seen_parts: dict[tuple[str, str], str]) -> list[Finding]:
    """Every check for one part file: schema, `[part]`, `[[function]]` and the facets."""
    data = parsed.data
    if data is None:
        return []
    path = parsed.path
    origins = parsed.origins
    part = data.get("part")
    part_line = _line(origins, ("part",)) if "part" in data else 1
    category = part.get("category") if type(part) is dict else None

    groups = (
        _check_top_level_tables(data, path, origins),
        _check_schema(data, path, library_schema),
        _check_part_section(data, part, path, part_line, seen_parts),
        _lint_function.check_functions(data, path, origins),
        _check_supplies(data, path, origins),
        _check_footprint(data, path, origins),
        _check_cable_product_section(data, path, origins, category, part_line),
        _check_pcb_section(data, path, origins, category, part_line),
        _ratings.check_part_rating(data, path, origins),
        _ratings.check_part_block(data, path, origins),
        _connection.check_part_connection(data, path, origins),
    )
    return [finding for group in groups for finding in group]


def _check_top_level_tables(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    return [
        _toml.finding("TABLE_UNKNOWN", path, _table_line(data, origins, key), f"unknown table {key!r}")
        for key in data
        if key != "schema" and key not in _PART_FILE_TABLES
    ]


def _table_line(data: _toml.Table, origins: _toml.Origins, key: str) -> int:
    """The header line of `key`, whether it is a single table or an array of tables."""
    if (key,) in origins:
        return origins[(key,)]
    if type(data[key]) is list:
        return _line(origins, (key, 0))
    return 1


def _check_schema(data: _toml.Table, path: str, library_schema: int | None) -> list[Finding]:
    if "schema" not in data:
        return [_toml.finding("FIELD_MISSING", path, 1, "part file is missing 'schema'")]
    raw_schema = data["schema"]
    if type(raw_schema) is not int:
        return [_toml.finding("FIELD_TYPE", path, 1, f"schema must be int, not {type(raw_schema).__name__}")]
    findings: list[Finding] = []
    if raw_schema not in SUPPORTED_SCHEMAS:
        findings.append(_schema_unsupported(path, 1, raw_schema))
    if library_schema is not None and raw_schema != library_schema:
        findings.append(
            _toml.finding(
                "SCHEMA_MIXED",
                path,
                1,
                f"schema {raw_schema} differs from library.toml's schema {library_schema}",
            )
        )
    return findings


def _check_part_section(data: _toml.Table, part: object, path: str, part_line: int, seen: dict[tuple[str, str], str]) -> list[Finding]:
    if "part" not in data:
        return [_toml.finding("FIELD_MISSING", path, 1, "part file has no [part] table")]
    findings = _fields.check_fields(part, _fields.PART_FIELDS, path=path, line=part_line, table_name="part")
    if type(part) is not dict:
        return findings
    findings.extend(_check_class_code(part.get("class_code"), path, part_line))
    findings.extend(_check_part_duplicate(part.get("manufacturer"), part.get("mpn"), path, part_line, seen))
    return findings


def _check_class_code(class_code: object, path: str, line: int) -> list[Finding]:
    if type(class_code) is not str:
        return []
    if _CLASS_CODE.fullmatch(class_code) is None:
        text = f"class_code {class_code!r} must be 1 to 3 uppercase letters"
    elif (rule := DESIGNATION_SCHEME.letter_rule(class_code)) is not None:
        text = f"class_code {class_code!r} is {rule} by IEC 81346-2:2019"
    else:
        return []
    return [_toml.finding("CLASS_CODE", path, line, text)]


def _check_part_duplicate(manufacturer: object, mpn: object, path: str, line: int, seen: dict[tuple[str, str], str]) -> list[Finding]:
    if type(manufacturer) is not str or type(mpn) is not str:
        return []
    earlier = seen.get((manufacturer, mpn))
    if earlier is None:
        seen[(manufacturer, mpn)] = path
        return []
    text = f"part ({manufacturer!r}, {mpn!r}) is already declared in {earlier}"
    return [_toml.finding("PART_DUPLICATE", path, line, text)]


def _check_supplies(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    if "supply" not in data:
        return []
    supplies = data["supply"]
    if type(supplies) is not list:
        return [_toml.finding("FIELD_TYPE", path, 1, "supply must be an array of tables")]
    findings: list[Finding] = []
    for index, supply in enumerate(supplies):
        line = _line(origins, ("supply", index))
        findings.extend(_fields.check_fields(supply, _fields.SUPPLY_FIELDS, path=path, line=line, table_name="supply"))
    return findings


def _check_footprint(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    if "footprint" not in data:
        return []
    line = _line(origins, ("footprint",))
    return _fields.check_fields(data["footprint"], _fields.FOOTPRINT_FIELDS, path=path, line=line, table_name="footprint")


def _check_cable_product_section(data: _toml.Table, path: str, origins: _toml.Origins, category: object, part_line: int) -> list[Finding]:
    if "cable_product" not in data:
        if category == "cable":
            return [
                _toml.finding(
                    "CABLE_WITHOUT_PRODUCT",
                    path,
                    part_line,
                    "category is cable with no [cable_product]",
                )
            ]
        return []
    line = _line(origins, ("cable_product",))
    cable_product = data["cable_product"]
    findings = _fields.check_fields(
        cable_product,
        _fields.CABLE_PRODUCT_FIELDS,
        path=path,
        line=line,
        table_name="cable_product",
    )
    if type(cable_product) is dict:
        core_count, colours = cable_product.get("core_count"), cable_product.get("core_colours")
        if type(core_count) is int and type(colours) is list and core_count != len(colours):
            findings.append(
                _toml.finding(
                    "CABLE_PRODUCT_CORE_COUNT",
                    path,
                    line,
                    f"core_count {core_count} does not match {len(colours)} core_colours",
                )
            )
        findings.extend(_cable_pairs.check_pairs(cable_product, path, line))
    if category is not None and category != "cable":
        findings.append(_toml.finding("CABLE_WITHOUT_PRODUCT", path, line, "[cable_product] is set on a non-cable part"))
    return findings


def _check_pcb_section(data: _toml.Table, path: str, origins: _toml.Origins, category: object, part_line: int) -> list[Finding]:
    if "pcb" not in data:
        if category == "board":
            return [
                _toml.finding(
                    "BOARD_WITHOUT_PCB",
                    path,
                    part_line,
                    "category is board with no [pcb]",
                )
            ]
        return []
    line = _line(origins, ("pcb",))
    return _fields.check_fields(data["pcb"], _fields.PCB_FIELDS, path=path, line=line, table_name="pcb")
