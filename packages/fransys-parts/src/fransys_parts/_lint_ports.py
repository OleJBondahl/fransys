"""Port and link checks of one `[[function]]` entry (`PORT_*`, `LINK_*`, `SYMBOL_PORT_*`)."""

from typing import TYPE_CHECKING

from . import _fields, _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def check_ports(entry: _toml.Table, symbol: object, path: str, line: int) -> list[Finding]:
    ports = entry.get("ports")
    if type(ports) is not list:
        return []
    if len(ports) == 0 and entry.get("kind") != "bar":
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


def check_links(entry: _toml.Table, path: str, line: int) -> list[Finding]:
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
