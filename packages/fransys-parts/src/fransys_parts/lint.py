"""Lint a part library without building a model (spec section 7, rulings P4-P8).

Every check is `ERROR` unless the call site passes `severity=Severity.WARNING`. Codes are
listed next to the check that raises them, and every finding's message carries its file
and line (`_toml.finding`, P6): `lint()` hands back bare findings with no model to resolve
an id's origin through, so the location lives in the text instead.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from fransys_model.derive import connector_label, connector_segments
from fransys_model.kernel import Finding, Severity

from . import _changeover, _fields, _function_facts, _joins, _power_loss, _ratings, _toml

if TYPE_CHECKING:
    from ._toml import ParsedFile

SUPPORTED_SCHEMAS: frozenset[int] = frozenset({1})

_FILE_NAME = re.compile(r"^[a-z0-9_-]+$")
_SYMBOL_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_CLASS_CODE = re.compile(r"^[A-Z]{1,3}$")

# IEC 81346-2:2019: "The letters A, I and O shall not be used as a class code."
_FORBIDDEN_CLASS_CODES: frozenset[str] = frozenset({"A", "I", "O"})
# IEC 81346-2:2019 reserves D, L, V, Y and Z. J is also reserved by the standard but is
# deliberately not in this set: the owner overrides IEC on J for connectors (spec C2).
_RESERVED_CLASS_CODES: frozenset[str] = frozenset({"D", "L", "V", "Y", "Z"})

_PART_FILE_TABLES = frozenset(
    {"part", "function", "supply", "footprint", "cable_product", "pcb", "rating"}
)


def lint(root: Path) -> tuple[Finding, ...]:
    """Check every part file under `root` against the part-file contract.

    Never raises for a malformed library, a missing `library.toml` included
    (`LIBRARY_FILE_MISSING`). Part files are read in name order, so the result does not
    depend on directory listing order (spec acceptance).
    """
    root = Path(root)
    library_file = root / "library.toml"
    if not library_file.is_file():
        return (
            _toml.finding(
                "LIBRARY_FILE_MISSING", "library.toml", 1, "no library.toml under this root"
            ),
        )

    findings: list[Finding] = []
    library = _toml.parse(library_file, relative_to=root)
    findings.extend(library.findings)
    library_schema: int | None = None
    if library.data is not None:
        findings.extend(
            _fields.check_fields(
                library.data,
                _fields.LIBRARY_FIELDS,
                path=library.path,
                line=1,
                table_name="library.toml",
            )
        )
        raw_schema = library.data.get("schema")
        if type(raw_schema) is int:
            library_schema = raw_schema
            if library_schema not in SUPPORTED_SCHEMAS:
                findings.append(_schema_unsupported(library.path, 1, library_schema))

    parts_dir = root / "parts"
    part_files = sorted(parts_dir.glob("*.toml")) if parts_dir.is_dir() else []
    seen_parts: dict[tuple[str, str], str] = {}
    for file_path in part_files:
        findings.extend(_lint_part_file(file_path, root, library_schema, seen_parts))
    return tuple(findings)


def _lint_part_file(
    file_path: Path, root: Path, library_schema: int | None, seen_parts: dict[tuple[str, str], str]
) -> list[Finding]:
    findings: list[Finding] = []
    rel_name = file_path.relative_to(root).as_posix()
    if _FILE_NAME.fullmatch(file_path.stem) is None:
        findings.append(
            _toml.finding(
                "FILE_NAME",
                rel_name,
                1,
                "a part file name should be lowercase with hyphens, digits and underscores",
                severity=Severity.WARNING,
            )
        )
    parsed = _toml.parse(file_path, relative_to=root)
    findings.extend(parsed.findings)
    if parsed.data is not None:
        findings.extend(_check_part_file(parsed, library_schema, seen_parts))
    return findings


def _schema_unsupported(path: str, line: int, value: int) -> Finding:
    supported = ", ".join(str(v) for v in sorted(SUPPORTED_SCHEMAS))
    return _toml.finding(
        "SCHEMA_UNSUPPORTED",
        path,
        line,
        f"schema {value} is not supported (supported: {supported})",
    )


def _line(origins: _toml.Origins, path_key: _toml.TablePath, default: int = 1) -> int:
    return origins.get(path_key, default)


def _check_part_file(
    parsed: ParsedFile, library_schema: int | None, seen_parts: dict[tuple[str, str], str]
) -> list[Finding]:
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
        _check_functions(data, path, origins),
        _check_supplies(data, path, origins),
        _check_footprint(data, path, origins),
        _check_cable_product_section(data, path, origins, category, part_line),
        _check_pcb_section(data, path, origins, category, part_line),
        _ratings.check_part_rating(data, path, origins),
        _power_loss.check_power_loss_twice(data, path, origins),
    )
    return [finding for group in groups for finding in group]


def _check_top_level_tables(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    return [
        _toml.finding(
            "TABLE_UNKNOWN", path, _table_line(data, origins, key), f"unknown table {key!r}"
        )
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
        return [
            _toml.finding(
                "FIELD_TYPE", path, 1, f"schema must be int, not {type(raw_schema).__name__}"
            )
        ]
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


def _check_part_section(
    data: _toml.Table, part: object, path: str, part_line: int, seen: dict[tuple[str, str], str]
) -> list[Finding]:
    if "part" not in data:
        return [_toml.finding("FIELD_MISSING", path, 1, "part file has no [part] table")]
    findings = _fields.check_fields(
        part, _fields.PART_FIELDS, path=path, line=part_line, table_name="part"
    )
    if type(part) is not dict:
        return findings
    findings.extend(_check_class_code(part.get("class_code"), path, part_line))
    findings.extend(
        _check_part_duplicate(part.get("manufacturer"), part.get("mpn"), path, part_line, seen)
    )
    return findings


def _check_class_code(class_code: object, path: str, line: int) -> list[Finding]:
    if type(class_code) is not str:
        return []
    if _CLASS_CODE.fullmatch(class_code) is None:
        text = f"class_code {class_code!r} must be 1 to 3 uppercase letters"
    elif class_code[0] in _FORBIDDEN_CLASS_CODES:
        text = f"class_code {class_code!r} is forbidden by IEC 81346-2:2019"
    elif class_code[0] in _RESERVED_CLASS_CODES:
        text = f"class_code {class_code!r} is reserved by IEC 81346-2:2019"
    else:
        return []
    return [_toml.finding("CLASS_CODE", path, line, text)]


def _check_part_duplicate(
    manufacturer: object, mpn: object, path: str, line: int, seen: dict[tuple[str, str], str]
) -> list[Finding]:
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
        findings.extend(
            _fields.check_fields(
                supply, _fields.SUPPLY_FIELDS, path=path, line=line, table_name="supply"
            )
        )
    return findings


def _check_footprint(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    if "footprint" not in data:
        return []
    line = _line(origins, ("footprint",))
    return _fields.check_fields(
        data["footprint"], _fields.FOOTPRINT_FIELDS, path=path, line=line, table_name="footprint"
    )


def _check_cable_product_section(
    data: _toml.Table, path: str, origins: _toml.Origins, category: object, part_line: int
) -> list[Finding]:
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
                    "CABLE_CORE_COUNT",
                    path,
                    line,
                    f"core_count {core_count} does not match {len(colours)} core_colours",
                )
            )
    if category is not None and category != "cable":
        findings.append(
            _toml.finding(
                "CABLE_WITHOUT_PRODUCT", path, line, "[cable_product] is set on a non-cable part"
            )
        )
    return findings


def _check_pcb_section(
    data: _toml.Table, path: str, origins: _toml.Origins, category: object, part_line: int
) -> list[Finding]:
    if "pcb" not in data:
        if category == "board":
            return [
                _toml.finding(
                    "BOARD_WITHOUT_PCB",
                    path,
                    part_line,
                    "category is board with no [pcb]",
                    severity=Severity.WARNING,
                )
            ]
        return []
    line = _line(origins, ("pcb",))
    return _fields.check_fields(
        data["pcb"], _fields.PCB_FIELDS, path=path, line=line, table_name="pcb"
    )


@dataclass(slots=True)
class _FunctionState:
    """What one part's functions are checked against each other with, in function order."""

    names_seen: set[str]
    plc_seen: set[tuple[object, object]]
    port_holders: dict[str, list[tuple[str, str]]]
    labels_seen: dict[str, str]
    segments: tuple[str, ...]


def _check_functions(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    if "function" not in data:
        return []
    functions = data["function"]
    if type(functions) is not list:
        return [_toml.finding("FIELD_TYPE", path, 1, "function must be an array of tables")]
    findings: list[Finding] = []
    segments = connector_segments(
        _connector_label(e) if type(e) is dict else None for e in functions
    )
    state = _FunctionState(
        names_seen=set(), plc_seen=set(), port_holders={}, labels_seen={}, segments=segments
    )
    for index, entry in enumerate(functions):
        line = _line(origins, ("function", index))
        if not isinstance(entry, dict):  # isinstance narrows to a dict ty accepts as a Table
            findings.append(
                _toml.finding("FIELD_TYPE", path, line, "function entry must be a table")
            )
            continue
        findings.extend(_check_function_entry(entry, path, line, state, index))
        findings.extend(_ratings.check_function_tables(entry, path, origins, index, line))
    return [*findings, *_joins.check(functions, path, origins)]


def _check_function_entry(
    entry: _toml.Table, path: str, line: int, state: _FunctionState, index: int
) -> list[Finding]:
    sub_tables = ("connector", "plc_channel", "rating", "operating", "protection")
    body = {k: v for k, v in entry.items() if k not in sub_tables}
    findings = _fields.check_fields(
        body, _fields.FUNCTION_FIELDS, path=path, line=line, table_name="function"
    )

    name = entry.get("name")
    if type(name) is str:
        if name in state.names_seen:
            findings.append(
                _toml.finding(
                    "FUNCTION_NAME_DUPLICATE",
                    path,
                    line,
                    f"function name {name!r} repeats within this part",
                )
            )
        state.names_seen.add(name)

    symbol = entry.get("symbol")
    if type(symbol) is str and _SYMBOL_SLUG.fullmatch(symbol) is None:
        findings.append(
            _toml.finding(
                "SYMBOL_SLUG", path, line, f"symbol {symbol!r} must be a lowercase, hyphenated slug"
            )
        )

    findings.extend(_check_ports(entry, symbol, path, line))
    findings.extend(_check_port_names_shared(entry, path, line, state, index))
    findings.extend(_check_links(entry, path, line))
    findings.extend(_changeover.check(entry, path, line))
    findings.extend(_function_facts.check(entry, path, line))
    findings.extend(_check_connector_facet(entry, path, line))
    findings.extend(_check_connector_marking_reused(entry, path, line, state))
    findings.extend(_check_plc_channel_facet(entry, path, line, state.plc_seen))
    return findings


def _connector_label(entry: _toml.Table) -> str | None:
    """The label a connector function prints, or `None` (parts-0003, `derive.connector_label`).

    `None` too for a non-string `marking` (`FIELD_TYPE` reports it); the rule is `derive`'s.
    """
    name = entry.get("name")
    if entry.get("kind") != "connector" or type(name) is not str:
        return None
    connector = entry.get("connector")
    marking = connector.get("marking") if type(connector) is dict else None
    if marking is not None and type(marking) is not str:
        return None
    return connector_label(marking, name)


def _check_port_names_shared(
    entry: _toml.Table, path: str, line: int, state: _FunctionState, index: int
) -> list[Finding]:
    """`PORT_NAME_SHARED`: same-named ports of two functions print one designation (parts-0005).

    A port prints `<item><segment>:<name>`; `derive.connector_segments` decides the segment.
    """
    ports = entry.get("ports")
    if type(ports) is not list:
        return []
    name = entry.get("name")
    function = name if type(name) is str else "<unnamed>"
    segment = state.segments[index]
    findings: list[Finding] = []
    named = (p.get("name") for p in ports if type(p) is dict)
    for port_name in dict.fromkeys(n for n in named if type(n) is str):
        holders = state.port_holders.setdefault(port_name, [])
        clash = next((h for h, other in holders if other == segment), None)
        if clash is not None:
            findings.append(
                _toml.finding(
                    "PORT_NAME_SHARED",
                    path,
                    line,
                    f"port name {port_name!r} is on both function {clash!r} and function "
                    f"{function!r}, which would print one designation, "
                    f"{f'<item>{segment}:{port_name}'!r}",
                )
            )
        holders.append((function, segment))
    return findings


def _check_connector_marking_reused(
    entry: _toml.Table, path: str, line: int, state: _FunctionState
) -> list[Finding]:
    """`CONNECTOR_MARKING_REUSED`: two connector functions of one part print one label."""
    label = _connector_label(entry)
    if label is None:
        return []
    name = entry["name"]
    earlier = state.labels_seen.get(label)
    if earlier is None:
        state.labels_seen[label] = name
        return []
    return [
        _toml.finding(
            "CONNECTOR_MARKING_REUSED",
            path,
            line,
            f"connector label {label!r} is printed by both function {earlier!r} and "
            f"function {name!r}",
        )
    ]


def _check_connector_facet(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    if "connector" not in entry:
        return []
    connector = entry["connector"]
    findings = _fields.check_fields(
        connector, _fields.CONNECTOR_FIELDS, path=path, line=line, table_name="function.connector"
    )
    if entry.get("kind") != "connector":
        findings.append(
            _toml.finding(
                "FACET_KIND_MISMATCH",
                path,
                line,
                "[function.connector] is set on a function whose kind is not connector",
            )
        )
    pincount = connector.get("pincount") if type(connector) is dict else None
    if type(pincount) is int and pincount < 1:
        findings.append(_toml.finding("PINCOUNT", path, line, f"pincount {pincount} is below 1"))
    return findings


def _check_plc_channel_facet(
    entry: _toml.Table, path: str, line: int, plc_seen: set[tuple[object, object]]
) -> list[Finding]:
    if "plc_channel" not in entry:
        return []
    plc = entry["plc_channel"]
    findings = _fields.check_fields(
        plc, _fields.PLC_CHANNEL_FIELDS, path=path, line=line, table_name="function.plc_channel"
    )
    if entry.get("kind") != "plc_channel":
        findings.append(
            _toml.finding(
                "FACET_KIND_MISMATCH",
                path,
                line,
                "[function.plc_channel] is set on a function whose kind is not plc_channel",
            )
        )
    if type(plc) is dict:
        dup_key = (plc.get("channel"), plc.get("signal"))
        if dup_key in plc_seen:
            findings.append(
                _toml.finding(
                    "PLC_CHANNEL_DUPLICATE",
                    path,
                    line,
                    f"channel {dup_key[0]!r} signal {dup_key[1]!r} repeats within this part",
                )
            )
        else:
            plc_seen.add(dup_key)
    return findings


def _check_ports(entry: _toml.Table, symbol: object, path: str, line: int) -> list[Finding]:
    ports = entry.get("ports")
    if type(ports) is not list:
        return []
    if len(ports) == 0:
        return [_toml.finding("FUNCTION_WITHOUT_PORTS", path, line, "function has no ports")]
    findings: list[Finding] = []
    names_seen: set[str] = set()
    for port in ports:
        if type(port) is not dict:
            findings.append(_toml.finding("FIELD_TYPE", path, line, "port entry must be a table"))
            continue
        findings.extend(
            _fields.check_fields(port, _fields.PORT_FIELDS, path=path, line=line, table_name="port")
        )
        name = port.get("name")
        if type(name) is str:
            if name in names_seen:
                findings.append(
                    _toml.finding(
                        "PORT_NAME_DUPLICATE",
                        path,
                        line,
                        f"port name {name!r} repeats within this function",
                    )
                )
            names_seen.add(name)
        if "symbol_port" in port and type(symbol) is not str:
            findings.append(
                _toml.finding(
                    "SYMBOL_PORT_WITHOUT_SYMBOL",
                    path,
                    line,
                    f"port {name!r} has symbol_port with no function symbol",
                )
            )
    return findings


def _check_links(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    links = entry.get("links")
    if type(links) is not list:
        return []
    ports = entry.get("ports")
    port_names = {p.get("name") for p in ports if type(p) is dict} if type(ports) is list else set()
    findings: list[Finding] = []
    seen_pairs: set[tuple[str, str]] = set()
    for link in links:
        if type(link) is not dict:
            findings.append(_toml.finding("FIELD_TYPE", path, line, "link entry must be a table"))
            continue
        findings.extend(
            _fields.check_fields(link, _fields.LINK_FIELDS, path=path, line=line, table_name="link")
        )
        a, b = link.get("a"), link.get("b")
        if type(a) is not str or type(b) is not str:
            continue
        if a not in port_names or b not in port_names:
            findings.append(
                _toml.finding(
                    "LINK_PORT_UNKNOWN",
                    path,
                    line,
                    f"link ({a!r}, {b!r}) names a port this function lacks",
                )
            )
        elif a == b:
            findings.append(
                _toml.finding("LINK_SELF", path, line, f"link joins port {a!r} to itself")
            )
        else:
            pair = (a, b) if a < b else (b, a)
            if pair in seen_pairs:
                findings.append(
                    _toml.finding("LINK_DUPLICATE", path, line, f"link ({a!r}, {b!r}) repeats")
                )
            else:
                seen_pairs.add(pair)
    return findings
