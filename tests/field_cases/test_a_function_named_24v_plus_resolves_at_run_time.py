"""Field case: a power module whose supply functions are named with + and - is reachable by its generated attribute.
The bug: the generator wrote P_24V_ for both (a silent clash), and at run time the device matched raw names only, so the attribute raised.
Fixed by author-0035, one function maps + to _plus and - to _minus, and a clash that is left fails generation."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.parts_module import parts_module

if TYPE_CHECKING:
    from pathlib import Path


_FUNCTION = (
    '\n[[function]]\nname = "{name}"\nkind = "protection"\n'
    'ports = [\n    {{ name = "{pin}", role = "generic" }},\n]\n'
    '\n[function.block]\ntype = "mcb"\n'
)
_PART = 'schema = 2\n\n[part]\nmpn = "PLANT-24V"\nmanufacturer = "Plant"\ndescription = "Planted part"\ncategory = "protection"\nclass_code = "F"\n'


# Names no other test imports: sys.modules caches by name, a shared one reads another tree.
def _library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...],
    name: str = "fieldcase_plant_parts",
) -> str:
    package = tmp_path / name
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        f'schema = 2\nname = "{name}"\nversion = "0.1.0"\ndescription = "Planted"\n',
        encoding="utf-8",
    )
    functions = "".join(_FUNCTION.format(name=n, pin=str(i + 1)) for i, n in enumerate(names))
    (package / "parts" / "plant.toml").write_text(_PART + functions, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


def test_a_plus_and_a_minus_function_resolve_by_attribute_and_by_raw_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library = _library(tmp_path, monkeypatch, ("24V+", "24V-"))
    text = parts_module(library)
    assert "    P_24V_plus: " in text
    assert "    P_24V_minus: " in text
    dev = fr.design(library, place="CAB").device("T1", "PLANT-24V")
    assert dev.P_24V_plus[1].name == "1"
    assert dev.P_24V_minus[2].name == "2"
    assert getattr(dev, "24V+")[1].name == "1"
    assert getattr(dev, "24V-")[2].name == "2"


def test_two_names_that_map_to_one_identifier_fail_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library = _library(tmp_path, monkeypatch, ("24V+", "24V_plus"), "fieldcase_clash_parts")
    with pytest.raises(fr.AuthorError, match=r"'24V\+' and '24V_plus'.*P_24V_plus"):
        parts_module(library)
