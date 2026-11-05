"""The typed parts module generator: names, collisions, determinism, digest."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from fransys.parts_module import _q, library_digest, parts_module
from fransys_author import AuthorError


def _part(mpn: str, pin: str = "1") -> str:
    return (
        f'schema = 2\n\n[part]\nmpn = "{mpn}"\nmanufacturer = "Plant"\n'
        'description = "Planted part"\ncategory = "protection"\nclass_code = "F"\n\n'
        '[[function]]\nname = "main"\nkind = "protection"\n'
        f'ports = [\n    {{ name = "{pin}", role = "generic" }},\n]\n'
        '\n[function.block]\ntype = "mcb"\n'
    )


def _plant(tmp_path, monkeypatch, name: str, parts: dict[str, str]) -> str:
    package = tmp_path / name
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        f'schema = 2\nname = "{name}"\nversion = "0.1.0"\ndescription = "Planted"\n',
        encoding="utf-8",
    )
    for file, text in parts.items():
        (package / "parts" / f"{file}.toml").write_text(text, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    # A package of this name an earlier test imported is in `sys.modules` and would be served
    # in place of this one, so the result would depend on test order.
    monkeypatch.delitem(sys.modules, name, raising=False)
    return name


def _classes(text: str) -> list[str]:
    return [x.split()[1].split("(")[0] for x in text.splitlines() if "(TypedDevice[" in x]


def _body(text: str) -> list[str]:
    return [x for x in text.splitlines() if not x.startswith(("SOURCES", '"""'))]


def test_demo_parts_class_names_and_literals() -> None:
    text = parts_module("demo_parts")
    ast.parse(text)
    for cls, mpn, fns in [
        ("DEMO_MCB_3P", "DEMO-MCB-3P", '"element"'),
        ("DEMO_OVERLOAD_3P", "DEMO-OVERLOAD-3P", '"aux", "main"'),
        ("DEMO_PB_NC", "DEMO-PB-NC", '"sw"'),
        ("DEMO_CTR_3P_24", "DEMO-CTR-3P-24", '"aux", "coil", "main"'),
    ]:
        head = f'class {cls}(TypedDevice[Literal[{fns}], "{cls}"]):'
        assert f'{head}\n    mpn: ClassVar[str] = "{mpn}"\n' in text
    assert "    aux: DEMO_OVERLOAD_3P__aux\n    main: DEMO_OVERLOAD_3P__main\n" in text
    assert 'm: Literal["95", 95, "96", 96]) -> Pin: ...' in text


def test_colliding_class_names_stop_before_emitting(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "clash_parts", {"a": _part("A-B"), "b": _part("A_B")})
    with pytest.raises(AuthorError, match=r"'A-B'.*'A_B'.*A_B"):
        parts_module(name)


def test_leading_digit_gets_a_prefix(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "digit_parts", {"a": _part("1ABC")})
    text = parts_module(name)
    ast.parse(text)
    assert 'class P_1ABC(TypedDevice[Literal["main"], "P_1ABC"]):\n    mpn: ClassVar[str] = "1ABC"' in text


def test_text_is_deterministic_and_sorted_by_mpn(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "zed_parts", {"a": _part("ZZ-1"), "b": _part("AA-1")})
    text = parts_module("demo_parts", name)
    assert text == parts_module("demo_parts", name)
    assert str(tmp_path) not in text
    names = _classes(text)
    assert names == sorted(names, key=lambda c: c.replace("_", "-"))
    assert names.index("AA_1") < names.index("ZZ_1")


def test_load_order_changes_only_the_sources_line(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "zed_parts", {"a": _part("ZZ-1")})
    assert library_digest("demo_parts", name) == library_digest(name, "demo_parts")
    first, second = parts_module("demo_parts", name), parts_module(name, "demo_parts")
    assert first != second
    assert _body(first) == _body(second)


def test_digest_ignores_whitespace_and_sees_facts(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "dig_parts", {"a": _part("DG-1")})
    path = tmp_path / name / "parts" / "a.toml"
    base = library_digest(name)
    path.write_text(path.read_text().replace("\n[part]", "\n\n\n[part]  "), encoding="utf-8")
    assert library_digest(name) == base
    path.write_text(path.read_text().replace("Planted part", "Other words"), encoding="utf-8")
    described = library_digest(name)
    assert described != base
    path.write_text(path.read_text().replace('name = "1"', 'name = "9"'), encoding="utf-8")
    assert library_digest(name) not in {base, described}


def test_digest_ignores_the_schema_version(monkeypatch) -> None:
    base = library_digest("demo_parts")
    monkeypatch.setattr("fransys_kernel.registry._Reg.schema_version", 99)
    assert library_digest("demo_parts") == base


def test_header_names_sources_and_digest() -> None:
    text = parts_module("demo_parts")
    assert "Generated from demo_parts." in text
    assert 'SOURCES = ("demo_parts",)' in text
    assert f'LIBRARY_DIGEST = "{library_digest("demo_parts")}"' in text


def test_every_pin_gets_an_attribute_named_by_the_one_identifier_rule() -> None:
    text = parts_module("demo_parts")
    assert "class DEMO_CTR_1P_MARKED__main(TypedFn):\n    P_1_L1: Pin\n    P_2_T1: Pin\n" in text
    assert "    P_24V1: Pin\n" in text  # unique on the device: on DEMO_PSU_24_MARKED itself
    device = text.split("class DEMO_CTR_1P_MARKED(")[1].split("\n\n")[0]
    assert "    P_1_L1: Pin\n    P_2_T1: Pin\n" in device  # a unique pin is on the device too


def test_two_pins_of_one_function_that_map_to_one_name_stop_the_generator(tmp_path, monkeypatch) -> None:
    text = _part("PIN-CLASH", "1/L1").replace(
        "]\n\n[function.block]",
        '    { name = "1_L1", role = "generic" },\n]\n\n[function.block]',
    )
    name = _plant(tmp_path, monkeypatch, "pin_clash_parts", {"a": text})
    with pytest.raises(AuthorError, match=r"'1/L1' and '1_L1' map to one name P_1_L1"):
        parts_module(name)


def test_a_marked_pin_is_reached_by_its_attribute_as_by_its_marking() -> None:
    import fransys as fr

    d = fr.design("demo_parts", place="C1")
    k = d.device("K1", "DEMO-CTR-1P-MARKED")
    psu = d.device("G1", "DEMO-PSU-24-MARKED")
    assert k.main.P_1_L1 is k.main["1/L1"]
    assert psu.P_24V1 is psu["24V1"]
    assert k.main.P_1_L1 is k["1/L1"]


def test_a_wrong_attribute_still_raises_and_lists_the_part_names() -> None:
    import fransys as fr

    d = fr.design("demo_parts", place="C1")
    k = d.device("K1", "DEMO-CTR-1P-MARKED")
    with pytest.raises(AttributeError, match=r"K1\.main has no pin 'P_1_L2'; pins: 1/L1, 2/T1"):
        k.main.P_1_L2  # noqa: B018 -- the access is the test
    with pytest.raises(AttributeError, match=r"K1 has no function or pin 'P_2_T2'"):
        k.P_2_T2  # noqa: B018 -- the access is the test


def test_a_changeover_function_declares_both_throws_and_a_contact_does_not() -> None:
    text = parts_module("demo_parts")
    assert "class DEMO_RLY_2CO_24__co_1(TypedFn):\n    no: Throw\n    nc: Throw\n" in text
    assert "from fransys import Pin, Throw, TypedDevice, TypedFn" in text
    coil = text.split("class DEMO_RLY_2CO_24__coil(")[1].split("\n\n")[0]
    assert "Throw" not in coil


def _ruff_format_clean(tmp_path: Path, source: str) -> None:
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    cmd = ["uv", "run", "ruff", "format", "--check", "--config", str(Path(__file__).parents[3] / "pyproject.toml"), str(path)]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 -- fixed arguments
    assert done.returncode == 0, done.stdout + done.stderr


def test_demo_parts_module_is_ruff_formatted(tmp_path: Path) -> None:
    _ruff_format_clean(tmp_path, parts_module("demo_parts"))


@pytest.mark.parametrize("text", ["plain", 'say "hi"', "it's", "both \" and '", 'back\\"slash', "tab\t"])
def test_a_quoted_string_is_what_ruff_format_keeps(tmp_path: Path, text: str) -> None:
    assert ast.literal_eval(_q(text)) == text
    _ruff_format_clean(tmp_path, f"X = {_q(text)}\n")
