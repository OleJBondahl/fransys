"""Ty proof: the unit recipe in `guide/units.md` type-checks, and a container reads its functions.

The recipe blocks are read from the guide, so the guide and this test cannot drift.
"""

import re
import subprocess
from importlib.resources import files
from pathlib import Path

from fransys.parts_module import parts_module

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "uv.lock").is_file())
USE = """

def use(d: fr.Design) -> None:
    io = d.add(box, "U1")
    io.X1.x1
    supply = d.add(supply_box, "U2")
    supply.X1.x1
    supply.rated
"""


def _recipe() -> str:
    text = files("fransys").joinpath("guide", "units.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    return "\n".join(b for b in blocks if "demo-supply-box" in b)


def _ty(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "demo_typed.py").write_text(parts_module("demo_parts"), encoding="utf-8")
    script = tmp_path / "recipe.py"
    script.write_text(source, encoding="utf-8")
    return subprocess.run(  # noqa: S603 -- the workspace's pinned ty, fixed arguments
        [
            *("uv", "run", "ty", "check", "--project", str(ROOT)),
            *("--extra-search-path", str(tmp_path), "--output-format", "concise", str(script)),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_unit_recipe_and_its_use_type_check_with_no_diagnostic(tmp_path) -> None:
    run = _ty(tmp_path, _recipe() + USE)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "ty: ignore" not in _recipe()
    assert "Any" not in _recipe()
