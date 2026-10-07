"""Header joins (parts-0017, HA4): `joins = "<function>.<port>"` loads; bad joins are refused.

Each refusal is an ERROR finding from `lint` and a `PartLibraryError` from `load_path`.
"""

from pathlib import Path

import demo_parts
import fransys_parts
import pytest
from fransys_parts import PartLibraryError

from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import port_templates

pytestmark = pytest.mark.wp("parts")

_LIBRARY = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
_HEAD = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "M"

[[function]]
name = "k1"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "A1", role = "generic", symbol_port = "in" },
    { name = "A2", role = "generic", symbol_port = "out" },
]

[function.operating]
nominal_voltage_v = "24"
resistance_ohm = "1600"
"""


def _connector(name, ports, marking):
    return f"""
[[function]]
name = "{name}"
kind = "connector"
symbol = "connector-fixed"
ports = [{", ".join(ports)}]

[function.connector]
style = "s"
pincount = {len(ports)}
gender = "male"
marking = "{marking}"
"""


def _pin(name, joins=None, symbol_port="in"):
    tail = f', joins = "{joins}"' if joins else ""
    return f'{{ name = "{name}", role = "generic", symbol_port = "{symbol_port}"{tail} }}'


def _library(tmp_path, body):
    (tmp_path / "library.toml").write_text(_LIBRARY)
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(_HEAD + body)
    return tmp_path


def _codes(root):
    return {finding.code: finding for finding in fransys_parts.lint(root)}


def test_a_header_joined_to_a_relay_port_lints_clean_and_stores_the_target_id_once(tmp_path):
    body = _connector("j1", [_pin("1", "k1.A1"), _pin("2", "k1.A2", "out")], "J1")
    root = _library(tmp_path, body)
    assert fransys_parts.lint(root) == ()

    templates = port_templates(freeze(fransys_parts.load_path(root)))
    by_name = {t.name: t for t in templates.values() if t.name in {"1", "2", "A1", "A2"}}
    assert by_name["1"].joins == by_name["A1"].id
    assert by_name["2"].joins == by_name["A2"].id
    assert by_name["A1"].joins is None
    assert sum(t.joins is not None for t in templates.values()) == 2


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (_connector("j1", [_pin("1", "k1.A9")], "J1"), "JOIN_PORT_UNKNOWN"),
        (_connector("j1", [_pin("1", "nope.A1")], "J1"), "JOIN_PORT_UNKNOWN"),
        (_connector("j1", [_pin("1", "garbage")], "J1"), "JOIN_PORT_UNKNOWN"),
        (
            _connector("j1", [_pin("1", "j2.1")], "J1") + _connector("j2", [_pin("1")], "J2"),
            "JOIN_INTO_CONNECTOR",
        ),
        (
            _connector("j1", [_pin("1", "k1.A1"), _pin("2", "k1.A1", "out")], "J1"),
            "JOIN_PORT_TWICE",
        ),
    ],
    ids=["missing-port", "missing-function", "malformed", "into-connector", "port-twice"],
)
def test_a_bad_join_is_an_error_finding_and_load_raises(tmp_path, body, code):
    root = _library(tmp_path, body)
    found = _codes(root)
    assert found[code].severity is Severity.ERROR
    with pytest.raises(PartLibraryError):
        fransys_parts.load_path(root)


def test_a_header_position_repeated_by_a_relay_port_is_port_name_shared(tmp_path):
    body = _connector("j1", [_pin("1", "r.1"), _pin("2", "r.2", "out")], "J1")
    relay = """
[[function]]
name = "r"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "1", role = "generic", symbol_port = "in" },
    { name = "2", role = "generic", symbol_port = "out" },
]

[function.operating]
nominal_voltage_v = "24"
resistance_ohm = "1600"
"""
    root = _library(tmp_path, relay + body)
    assert "PORT_NAME_SHARED" in _codes(root)


def test_the_same_pin_names_without_a_clash_do_not_trigger_port_name_shared(tmp_path):
    body = _connector("j1", [_pin("1", "k1.A1"), _pin("2", "k1.A2", "out")], "J1")
    assert "PORT_NAME_SHARED" not in _codes(_library(tmp_path, body))


def test_the_demo_relay_module_lints_clean_and_the_demo_library_loads():
    assert fransys_parts.lint(Path(demo_parts.__file__).parent) == ()
    templates = port_templates(freeze(fransys_parts.load("demo_parts")))
    joined = [t for t in templates.values() if t.joins is not None]
    assert len(joined) == 6
    assert {t.name for t in joined} == {"1", "2", "3", "4"}
