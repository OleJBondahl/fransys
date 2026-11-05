"""`migrate_part_text`: a schema 1 part file or `library.toml` as schema 2 text (MIGRATE-022-DROP; decision model-0369).

Pure: text in, text out, no file read or written. It rewrites the rating, operating and protection tables and
the `schema` line, keeps every other line, and raises `PartTextError` for a text it cannot convert.
0.23 deletes this module.
"""

import re
import tomllib
from typing import Any

from ._errors import PartTextError

_HEADER = re.compile(r"^\[\[?[A-Za-z_][\w.]*\]\]?$")
_OLD_TABLES = ("[rating]", "[function.operating]", "[function.rating]", "[function.protection]")
_UNITS = {"v": "V", "a": "A", "w": "W", "ohm": "ohm", "ms": "ms", "ah": "Ah"}
_OLD_KEYS = {
    "voltage_ac_v", "voltage_dc_v", "current_ac_a", "current_dc_a", "min_breaking_current_a",
    "power_loss_w", "breaking_ac", "breaking_dc", "nominal_voltage_v", "nominal_power_w",
    "nominal_current_a", "max_voltage_v", "min_voltage_v", "resistance_ohm", "max_current_ac_a",
    "max_current_dc_a", "fault_current_ac_a", "fault_current_dc_a", "fault_time_constant_ms",
}  # fmt: skip


def _rating_lines(table: dict[str, Any]) -> list[str]:
    lines = []
    for name, unit in (("voltage", "v"), ("current", "a")):
        items = [
            f'{{ nom = "{table[key]} {unit.upper()}", at = ["{kind.upper()}"] }}'
            for kind in ("ac", "dc")
            if (key := f"{name}_{kind}_{unit}") in table
        ]
        if items:
            lines.append(f"{name} = [{', '.join(items)}]")
    if "power_loss_w" in table:
        lines.append(f'power_loss = {{ nom = "{table["power_loss_w"]} W" }}')
    return lines


def _breaking_items(table: dict[str, Any]) -> list[str]:
    items = []
    if "min_breaking_current_a" in table:
        items.append(f'{{ min = "{table["min_breaking_current_a"]} A" }}')
    for kind in ("ac", "dc"):
        for point in table.get(f"breaking_{kind}", ()):
            at = [kind.upper(), f"{point['voltage_v']} V"]
            if "time_constant_ms" in point:
                at.append(f"{point['time_constant_ms']} ms")
            quoted = ", ".join(f'"{c}"' for c in at)
            items.append(f'{{ max = "{point["current_a"]} A", at = [{quoted}] }}')
    return items


def _fig(ends: dict[str, str], *current: str) -> str:
    at = f", at = [{', '.join(f'"{c.upper()}"' for c in current)}]" if current else ""
    return "{ " + ", ".join(f'{key} = "{value}"' for key, value in ends.items()) + at + " }"


def _voltage(values: dict[str, str]) -> list[str]:
    """The `voltage` figure list of the old voltage keys: one window, then one figure per current not in it."""
    window = {end: values[key] for end, key in (("nom", "nominal_voltage"), ("min", "min_voltage"), ("max", "max_voltage")) if key in values}
    sides = [(kind, values[f"voltage_{kind}"]) for kind in ("ac", "dc") if f"voltage_{kind}" in values]
    figures = []
    if window and len(sides) == 1:
        kind, value = sides.pop()
        figures.append(_fig({"nom": value, **window} if "nom" not in window else window, kind))
        sides = [(kind, value)] if value != window["nom"] else []
    elif window:
        figures.append(_fig(window))
    return [*figures, *(_fig({"nom": value}, kind) for kind, value in sides)]


def operating_lines(values: dict[str, str]) -> list[str]:
    """The schema 2 `[function.operating]` lines of old keys (`voltage_dc`, `max_current_ac`, ...) holding quantity strings."""
    lines = []
    if figures := _voltage(values):
        lines.append(f"voltage = [{', '.join(figures)}]")
    for stem in ("max_current", "fault_current"):
        sided = [_fig({"max": values[f"{stem}_{kind}"]}, kind) for kind in ("ac", "dc") if f"{stem}_{kind}" in values]
        lines += [f"{stem} = [{', '.join(sided)}]"] if sided else []
    old = ("voltage_", "nominal_voltage", "min_voltage", "max_voltage", "max_current_", "fault_current_")
    return lines + [f'{key} = "{value}"' for key, value in values.items() if not key.startswith(old)]


def _operating_lines(table: dict[str, Any]) -> list[str]:
    values = {}
    for key, value in table.items():
        stem, _, suffix = key.rpartition("_")
        values[stem] = f"{value} {_UNITS[suffix]}"
    return operating_lines(values)


def _segments(text: str) -> list[tuple[str, str]]:
    """(header line, body) pairs; the first pair is the text before any header."""
    segments: list[tuple[str, str]] = [("", "")]
    for line in text.splitlines(keepends=True):
        if _HEADER.match(line.strip()):
            segments.append((line, ""))
        else:
            header, body = segments[-1]
            segments[-1] = (header, body + line)
    return segments


def _block_lines(items: list[str], kind: object) -> list[str]:
    """The breaking keys of a block of type `kind`: a fuse lists them, a breaker states one point as `icu`."""
    if not items:
        return []
    if kind == "fuse":
        return [f"breaking_capacity = [{', '.join(items)}]"]
    if kind in ("mcb", "motor_breaker") and len(items) == 1 and items[0].startswith("{ max"):
        return [f"icu = {items[0]}"]
    msg = (
        f"{len(items)} breaking points on a {kind} cannot convert: "
        "split the breaker's breaking points into one per kind (a breaker states one point as icu), then migrate"
    )
    raise PartTextError(msg)


def _split_tail(body: str) -> tuple[str, str]:
    """The table text of a segment body and the blank and comment lines after its last key."""
    lines = body.splitlines(keepends=True)
    while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("#")):
        lines.pop()  # these belong to the next table
    content = "".join(lines)
    return content.rstrip("\n"), body[len(content) :]


def _parses(text: str) -> bool:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False
    return True


def _comment_of(line: str, name: str) -> list[str]:
    """The comment on one line of a table's text: a comment line, or the text from the first `#` that ends a whole key line."""
    if line.lstrip().startswith("#"):
        return [line.strip()]
    for index, char in enumerate(line):
        if char == "#" and _parses(line[:index]):
            return [line[index:].strip()]
    if _parses(line):  # every `#` is inside a quoted value
        return []
    msg = f"{name} holds a comment after a value spread over several lines: move it to a line of its own, then migrate"
    raise PartTextError(msg)


def _comments(content: str, name: str) -> list[str]:
    """Every comment of a table's text, own-line comments and the ends of key lines; they stay above the rewritten keys."""
    return [comment for line in content.splitlines() for comment in _comment_of(line, name)]


def _rating(header: str, table: dict[str, Any], items: list[str], *, in_function: bool) -> tuple[str, list[str]]:
    """The (header, lines) of an old `[rating]` table; a part-level one makes its breaking points a fuse `[block]`."""
    if items:
        msg = "breaking points need a [function.protection] type to convert: state them in a protection function"
        raise PartTextError(msg)
    lines = _rating_lines(table)
    if not in_function and (part_items := _breaking_items(table)):  # a fuse link's figures: a part-level [block]
        if not lines:
            return "[block]\n", ['type = "fuse"', *_block_lines(part_items, "fuse")]
        return header, [*lines, "", "[block]", 'type = "fuse"', *_block_lines(part_items, "fuse")]
    return header, lines


def _convert(header: str, body: str, items: list[str], *, in_function: bool) -> str:
    """One old-table segment as schema 2 text; `items` are the breaking figures it carries."""
    name = header.strip()
    content, tail = _split_tail(body)
    table = tomllib.loads(content)
    if name == "[function.protection]":
        header, lines = "[function.block]\n", [*content.splitlines(), *_block_lines(items, table.get("type"))]
    elif name == "[function.operating]":
        lines = _operating_lines(table)
    else:
        header, lines = _rating(header, table, items, in_function=in_function)
    if name != "[function.protection]":  # protection keeps its own lines, comments with them
        lines = [*_comments(content, name), *lines]
    return header + "\n".join(lines) + "\n" + tail if lines else tail


def _segment_texts(text: str, functions: list[dict[str, Any]]) -> str:
    breaking = [_breaking_items(f.get("rating", {})) for f in functions]
    out: list[str] = []
    index = -1
    for header, body in _segments(text):
        name = header.strip()
        index += name == "[[function]]"
        if name not in _OLD_TABLES:
            out.append(header + body)
            continue
        items = breaking[index] if name in _OLD_TABLES[2:] else []
        if name == "[function.rating]" and "protection" in functions[index]:
            items = []
        out.append(_convert(header, body, items, in_function=name != "[rating]"))
    return "".join(out)


def migrate_part_text(text: str) -> str:
    """The schema 2 text of a schema 1 file; a schema 2 file is returned unchanged."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        msg = f"the text is not valid TOML: {error}"
        raise PartTextError(msg) from error
    if data.get("schema") != 1:
        return text
    try:
        _refuse_bar(text, data.get("function", []))
        result = _segment_texts(text, data.get("function", []))
    except PartTextError as error:
        msg = f"part {data.get('part', {}).get('mpn', '?')}: {error}"
        raise PartTextError(msg) from error
    result = re.sub(r"^schema = 1$", "schema = 2", result, count=1, flags=re.MULTILINE)
    _refuse_leftovers(tomllib.loads(result))
    return result


def _refuse_bar(text: str, functions: list[dict[str, Any]]) -> None:
    """A PE bar function has no schema 2 spelling: refuse it, naming the line of its kind key or its table header."""
    index = next((i for i, entry in enumerate(functions) if entry.get("kind") == "bar"), None)
    if index is None:
        return
    rows = text.splitlines()
    headers = [n for n, row in enumerate(rows) if re.fullmatch(r"\s*\[\[function\]\]\s*(#.*)?", row)]
    start = headers[index] if index < len(headers) else 0
    stop = headers[index + 1] if index + 1 < len(headers) else len(rows)
    key = next((n for n in range(start, stop) if re.search(r"\bkind\s*=\s*[\"']bar[\"']", rows[n])), start)
    msg = (
        f'line {key + 1}: kind = "bar" (a PE bar part) is removed in 0.22: '
        "replace it with a PE terminal-strip part (moving-to-0.22.md#removed-cable-core-fn)"
    )
    raise PartTextError(msg)


def _refuse_leftovers(data: dict[str, Any]) -> None:
    tables = [data.get("rating", {})]
    for entry in data.get("function", ()):
        tables += [entry.get("rating", {}), entry.get("operating", {}), entry.get("protection", {})]
    if any(_OLD_KEYS & table.keys() for table in tables) or any("protection" in entry for entry in data.get("function", ())):
        msg = "a schema 1 table is left: write each table under its own [header] line"
        raise PartTextError(msg)
