"""Field case: a part function named with `+` or `-` is reachable by its generated attribute.

The engineering shape: a power module whose two supply functions are named `24V+` and `24V-`,
as the data sheet prints them. The typed parts module gives them attributes; the author writes
`dev.P_24V_plus` and `dev.P_24V_minus`, or `getattr(dev, "24V+")` for the raw name.

The bug: the generator wrote `P_24V_` for both (a silent clash), and at run time the device
matched raw names only, so the generated attribute raised.

The rule (decision author-0035): one function maps a raw function name to its identifier, `+` to
`_plus` and `-` to `_minus` before other characters become `_`. The generator and the device both
call it, and a clash that is left fails generation.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.parts_module import parts_module

if TYPE_CHECKING:
    from pathlib import Path


_FUNCTION = (
    '\n[[function]]\nname = "{name}"\nkind = "protection"\n'
    'ports = [\n    {{ name = "{pin}", role = "generic" }},\n]\n'
    '\n[function.protection]\ntype = "mcb"\n'
)
_PART = (
    'schema = 1\n\n[part]\nmpn = "PLANT-24V"\nmanufacturer = "Plant"\n'
    'description = "Planted part"\ncategory = "protection"\nclass_code = "F"\n'
)


def _library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...],
    name: str = "plant_parts",
) -> str:
    package = tmp_path / name
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        f'schema = 1\nname = "{name}"\nversion = "0.1.0"\ndescription = "Planted"\n',
        encoding="utf-8",
    )
    functions = "".join(_FUNCTION.format(name=n, pin=str(i + 1)) for i, n in enumerate(names))
    (package / "parts" / "plant.toml").write_text(_PART + functions, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


def test_a_plus_and_a_minus_function_resolve_by_attribute_and_by_raw_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path, monkeypatch, ("24V+", "24V-"))
    text = parts_module(library)
    assert "    P_24V_plus: " in text
    assert "    P_24V_minus: " in text
    dev = fr.design(library, place="CAB").device("T1", "PLANT-24V")
    assert dev.P_24V_plus[1].name == "1"
    assert dev.P_24V_minus[2].name == "2"
    assert getattr(dev, "24V+")[1].name == "1"
    assert getattr(dev, "24V-")[2].name == "2"


def test_two_names_that_map_to_one_identifier_fail_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _library(tmp_path, monkeypatch, ("24V+", "24V_plus"), "clash_parts")
    with pytest.raises(fr.AuthorError, match=r"'24V\+' and '24V_plus'.*P_24V_plus"):
        parts_module(library)
