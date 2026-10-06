"""Rest state and protection type lints (ELECTRICAL-FACTS F2, F3): each fires on a planted part.

`_codes` reads back the finding codes `lint` returned, so a test checks the code it owns. Every
planted case has a clean twin: the same function with the one fact fixed.
"""

import itertools

import fransys_parts
import pytest

from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import (
    Energy,
    LinkRest,
    ProtectionType,
    function_templates,
    internal_links,
    parts,
)

_LIBRARY = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_HEAD = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"

"""
_PORTS = 'ports = [{ name = "1", role = "generic" }, { name = "2", role = "generic" }]'
_roots = itertools.count()


def _lint(tmp_path, function):
    root = tmp_path / f"lib-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(_HEAD + function)
    return fransys_parts.lint(root)


def _codes(tmp_path, function):
    return {f.code for f in _lint(tmp_path, function)}


def _switch(kind="switch", rest=None, symbol=None, links=None):
    rest_text = "" if rest is None else f', rest = "{rest}"'
    symbol_text = "" if symbol is None else f'symbol = "{symbol}"\n'
    link_text = (
        links if links is not None else f'{{ a = "1", b = "2", kind = "switched"{rest_text} }}'
    )
    body = "" if link_text == "" else f"links = [{link_text}]\n"
    return f'[[function]]\nname = "k"\nkind = "{kind}"\n{symbol_text}{_PORTS}\n{body}'


def _protection(type_=None, symbol=None, link_kind="protective"):
    symbol_text = "" if symbol is None else f'symbol = "{symbol}"\n'
    table = "" if type_ is None else f'\n[function.protection]\ntype = "{type_}"\n'
    links = f'links = [{{ a = "1", b = "2", kind = "{link_kind}" }}]\n'
    return f'[[function]]\nname = "e"\nkind = "protection"\n{symbol_text}{_PORTS}\n{links}{table}'


@pytest.mark.parametrize("kind", ["switch", "generic"])
def test_switched_link_without_rest(tmp_path, kind):
    assert "SWITCHED_LINK_WITHOUT_REST" in _codes(tmp_path, _switch(kind))
    for rest in ("open", "closed"):
        assert "SWITCHED_LINK_WITHOUT_REST" not in _codes(tmp_path, _switch(kind, rest=rest))


def test_a_contact_kind_needs_no_declared_rest(tmp_path):
    for kind in ("contact_no", "contact_nc"):
        assert "SWITCHED_LINK_WITHOUT_REST" not in _codes(tmp_path, _switch(kind))


def test_an_invalid_rest_value_is_an_enum_finding(tmp_path):
    assert "ENUM_VALUE" in _codes(tmp_path, _switch(rest="ajar"))


@pytest.mark.parametrize(
    ("kind", "rest", "fires"),
    [
        ("contact_no", "closed", True),
        ("contact_nc", "open", True),
        ("contact_no", "open", False),
        ("contact_nc", "closed", False),
        ("contact_no", None, False),
    ],
)
def test_rest_disagrees_with_kind(tmp_path, kind, rest, fires):
    found = [
        f for f in _lint(tmp_path, _switch(kind, rest=rest)) if f.code == "REST_DISAGREES_WITH_KIND"
    ]
    assert [f.severity for f in found] == ([Severity.ERROR] if fires else [])


@pytest.mark.parametrize("kind", ["contact_no", "contact_nc", "contact_co", "switch"])
def test_contact_without_switched_link(tmp_path, kind):
    bare = _switch(kind, links="")
    assert "CONTACT_WITHOUT_SWITCHED_LINK" in _codes(tmp_path, bare)
    conductive = _switch(kind, links='{ a = "1", b = "2", kind = "conductive" }')
    assert "CONTACT_WITHOUT_SWITCHED_LINK" in _codes(tmp_path, conductive)
    assert "CONTACT_WITHOUT_SWITCHED_LINK" not in _codes(tmp_path, _switch(kind, rest="open"))


def test_a_generic_function_needs_no_switched_link(tmp_path):
    assert "CONTACT_WITHOUT_SWITCHED_LINK" not in _codes(tmp_path, _switch("generic", links=""))


@pytest.mark.parametrize(
    ("kind", "rest", "symbol", "fires"),
    [
        ("switch", "open", "break-contact", True),
        ("switch", "closed", "make-contact", True),
        ("contact_no", None, "break-contact", True),
        ("contact_nc", None, "make-contact", True),
        ("switch", "open", "make-contact", False),
        ("switch", "closed", "break-contact", False),
        ("contact_no", None, "make-contact", False),
        ("switch", "closed", "some-other-symbol", False),
        ("switch", "open", "emergency-stop", True),
        ("switch", "closed", "emergency-stop", False),
    ],
)
def test_symbol_rest_mismatch(tmp_path, kind, rest, symbol, fires):
    codes = _codes(tmp_path, _switch(kind, rest=rest, symbol=symbol))
    assert ("SYMBOL_REST_MISMATCH" in codes) is fires


@pytest.mark.parametrize(
    ("type_", "fires"), [(None, True), ("fuse", False), ("rcd", False), ("overload", False)]
)
def test_protection_without_type_is_a_warning(tmp_path, type_, fires):
    found = [f for f in _lint(tmp_path, _protection(type_)) if f.code == "PROTECTION_WITHOUT_TYPE"]
    assert [f.severity for f in found] == ([Severity.WARNING] if fires else [])


def test_an_invalid_protection_type_is_refused_and_an_unknown_field_too(tmp_path):
    assert "ENUM_VALUE" in _codes(tmp_path, _protection("breaker"))
    unknown = _protection("fuse") + "poles = 2\n"
    assert "FIELD_UNKNOWN" in _codes(tmp_path, unknown)
    for type_ in ("fuse", "mcb", "motor_breaker", "overload", "rcd"):
        assert _codes(tmp_path, _protection(type_)) == set()


@pytest.mark.parametrize(
    ("type_", "symbol", "fires"),
    [
        ("mcb", "fuse", True),
        ("fuse", "circuit-breaker", True),
        ("fuse", "fuse", False),
        ("mcb", "circuit-breaker", False),
        ("rcd", "fuse", True),
        ("fuse", "some-other-symbol", False),
    ],
)
def test_symbol_type_mismatch(tmp_path, type_, symbol, fires):
    codes = _codes(tmp_path, _protection(type_, symbol))
    assert ("SYMBOL_TYPE_MISMATCH" in codes) is fires


def test_rest_loads_into_the_model_and_an_undeclared_link_has_none(tmp_path):
    for kind, rest, expected in (
        ("switch", "closed", LinkRest.CLOSED),
        ("switch", "open", LinkRest.OPEN),
        ("contact_no", None, None),
    ):
        root = tmp_path / f"load-{next(_roots)}"
        (root / "parts").mkdir(parents=True)
        (root / "library.toml").write_text(_LIBRARY)
        (root / "parts" / "p.toml").write_text(_HEAD + _switch(kind, rest=rest))
        model = freeze(fransys_parts.load_path(root))
        (link,) = internal_links(model).values()
        assert link.rest is expected


@pytest.mark.parametrize("type_", [None, "fuse", "motor_breaker"])
def test_a_protection_type_loads_into_the_model_and_an_undeclared_one_is_none(tmp_path, type_):
    model = freeze(fransys_parts.load_path(_one(tmp_path, _protection(type_))))
    (function,) = function_templates(model).values()
    assert function.protection_type == (None if type_ is None else ProtectionType(type_))


def test_a_protection_type_on_another_kind_is_refused(tmp_path):
    table = '\n[function.protection]\ntype = "fuse"\n'
    planted = _switch(rest="open") + table
    assert "PROTECTION_TYPE_ON_NON_PROTECTION" in _codes(tmp_path, planted)
    assert "PROTECTION_TYPE_ON_NON_PROTECTION" not in _codes(tmp_path, _switch(rest="open"))
    with pytest.raises(fransys_parts.PartLibraryError):
        fransys_parts.load_path(_one(tmp_path, planted))


def _one(tmp_path, function):
    root = tmp_path / f"one-{next(_roots)}"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "p.toml").write_text(_HEAD + function)
    return root


def test_rest_on_an_unswitched_link_is_refused(tmp_path):
    planted = _switch(links='{ a = "1", b = "2", kind = "conductive", rest = "open" }')
    assert "REST_ON_UNSWITCHED_LINK" in _codes(tmp_path, planted)
    assert "REST_ON_UNSWITCHED_LINK" not in _codes(tmp_path, _switch(rest="open"))


@pytest.mark.parametrize(
    ("part", "expected"),
    [
        ("fuse-abat", ProtectionType.FUSE),
        ("mcb-c6", ProtectionType.MCB),
        ("mcb-2p", ProtectionType.MCB),
    ],
)
def test_demo_protection_parts_carry_their_type(part, expected):
    model = freeze(fransys_parts.load("demo_parts"))
    (part_id,) = (p.id for p in parts(model).values() if p.mpn.lower().endswith(part))
    types = {f.protection_type for f in function_templates(model).values() if f.part == part_id}
    assert expected in types


def test_the_protection_types_are_the_part_files_spelling():
    """Each member's value is the string a part file writes under `[function.protection]`."""
    members = (
        ProtectionType.MOTOR_BREAKER,
        ProtectionType.OVERLOAD,
        ProtectionType.RCD,
    )
    assert [m.value for m in members] == ["motor_breaker", "overload", "rcd"]


def _supply(energy=None, kind="supply"):
    text = "" if energy is None else f'energy = "{energy}"\n'
    return f'[[function]]\nname = "s"\nkind = "{kind}"\n{text}{_PORTS}\n'


@pytest.mark.parametrize(
    ("energy", "expected"), [(None, None), ("in", Energy.IN), ("out", Energy.OUT)]
)
def test_an_energy_loads_into_the_model_and_an_undeclared_one_is_none(tmp_path, energy, expected):
    model = freeze(fransys_parts.load_path(_one(tmp_path, _supply(energy))))
    (function,) = function_templates(model).values()
    assert function.energy is expected


def test_an_energy_on_another_kind_is_refused(tmp_path):
    planted = _supply("in", kind="coil")
    assert "ENERGY_ON_NON_POWER" in _codes(tmp_path, planted)
    assert "ENERGY_ON_NON_POWER" not in _codes(tmp_path, _supply("in"))
    assert "ENERGY_ON_NON_POWER" not in _codes(tmp_path, _supply("out", kind="load"))
    with pytest.raises(fransys_parts.PartLibraryError):
        fransys_parts.load_path(_one(tmp_path, planted))


def test_an_energy_that_is_not_in_or_out_is_an_enum_error(tmp_path):
    assert "ENUM_VALUE" in _codes(tmp_path, _supply("sideways"))
