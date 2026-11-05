"""A terminal part's `[connection]`: the elecdef `Connection` a part-level table states (R1268)."""

from fransys_model.elecdef import Connection
from fransys_model.kernel import Draft, Finding, Origin, make_id
from fransys_model.vocab import BlockFacet, FunctionTemplate

from . import _fields, _toml

# KI-482 (LIB-CONNECTION): only conductors_per_clamp is read; the rest of the elecdef Connection waits until after 0.22.
__all__ = ["add_part_connection", "check_part_connection"]


def check_part_connection(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    """Check a top-level `[connection]`: one function, `conductors_per_clamp` a whole number from 1; nothing when absent."""
    if "connection" not in data:
        return []
    line = origins.get(("connection",), 1)
    table = data["connection"]
    findings = _fields.check_fields(table, _fields.CONNECTION_FIELDS, path=path, line=line, table_name="connection")
    if len(data.get("function", ())) != 1:
        text = "a part-level [connection] is the connection of a part's one function"
        findings.append(_toml.finding("RATING_VALUE_INVALID", path, line, text))
    elif not findings and table["conductors_per_clamp"] < 1:
        findings.append(_toml.finding("RATING_VALUE_INVALID", path, line, "conductors_per_clamp is at least 1"))
    return findings


def add_part_connection(draft: Draft, data: _toml.Table, part_key: tuple[str, ...], path: str, origins: _toml.Origins) -> None:
    """Add the `BlockFacet` of a lint-clean part-level `[connection]`: the `Connection` of the part's one template."""
    if "connection" in data:
        function_key = (*part_key, "function", data["function"][0]["name"])
        key = (*function_key, "connection")
        block = Connection(conductors_per_clamp=data["connection"]["conductors_per_clamp"])
        origin = Origin(file=path, line=origins.get(("connection",), 1), note="")
        draft.add(BlockFacet(id=make_id(BlockFacet, key), key=key, subject=make_id(FunctionTemplate, function_key), block=block), origin=origin)
