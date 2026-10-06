"""The typed parts module generator: names, collisions, determinism, digest (EA4)."""

import ast

import pytest
from fransys.parts_module import library_digest, parts_module
from fransys_author import AuthorError


def _part(mpn: str, pin: str = "1") -> str:
    return (
        f'schema = 1\n\n[part]\nmpn = "{mpn}"\nmanufacturer = "Plant"\n'
        'description = "Planted part"\ncategory = "protection"\nclass_code = "F"\n\n'
        '[[function]]\nname = "main"\nkind = "protection"\n'
        f'ports = [\n    {{ name = "{pin}", role = "generic" }},\n]\n'
        '\n[function.protection]\ntype = "mcb"\n'
    )


def _plant(tmp_path, monkeypatch, name: str, parts: dict[str, str]) -> str:
    package = tmp_path / name
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        f'schema = 1\nname = "{name}"\nversion = "0.1.0"\ndescription = "Planted"\n',
        encoding="utf-8",
    )
    for file, text in parts.items():
        (package / "parts" / f"{file}.toml").write_text(text, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


def _classes(text: str) -> list[str]:
    return [x.split()[1].split("(")[0] for x in text.splitlines() if "(TypedDevice[" in x]


def _body(text: str) -> list[str]:
    return [x for x in text.splitlines() if not x.startswith(("SOURCES", '"""'))]


def test_demo_parts_class_names_and_literals() -> None:
    text = parts_module("demo_parts")
    ast.parse(text)
    for cls, mpn, fns in [
        ("DEMO_MCB_3P", "DEMO-MCB-3P", "'element'"),
        ("DEMO_OVERLOAD_3P", "DEMO-OVERLOAD-3P", "'aux', 'main'"),
        ("DEMO_PB_NC", "DEMO-PB-NC", "'sw'"),
        ("DEMO_CTR_3P_24", "DEMO-CTR-3P-24", "'aux', 'coil', 'main'"),
    ]:
        head = f"class {cls}(TypedDevice[Literal[{fns}], {cls!r}]):"
        assert f"{head}\n    mpn: ClassVar[str] = {mpn!r}\n" in text
    assert "    aux: DEMO_OVERLOAD_3P__aux\n    main: DEMO_OVERLOAD_3P__main\n" in text
    assert "m: Literal['95', 95, '96', 96]) -> Pin: ..." in text


def test_colliding_class_names_stop_before_emitting(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "clash_parts", {"a": _part("A-B"), "b": _part("A_B")})
    with pytest.raises(AuthorError, match=r"'A-B'.*'A_B'.*A_B"):
        parts_module(name)


def test_leading_digit_gets_a_prefix(tmp_path, monkeypatch) -> None:
    name = _plant(tmp_path, monkeypatch, "digit_parts", {"a": _part("1ABC")})
    text = parts_module(name)
    ast.parse(text)
    assert (
        "class P_1ABC(TypedDevice[Literal['main'], 'P_1ABC']):\n    mpn: ClassVar[str] = '1ABC'"
        in text
    )


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


def test_header_names_sources_and_digest() -> None:
    text = parts_module("demo_parts")
    assert "Generated from demo_parts." in text
    assert "SOURCES = ('demo_parts',)" in text
    assert f"LIBRARY_DIGEST = {library_digest('demo_parts')!r}" in text
