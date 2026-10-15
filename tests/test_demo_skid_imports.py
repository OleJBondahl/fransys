"""The demo skid imports `fransys` and the standard library only (DEMO-SKID K1, acceptance 2).

A design in `examples/demo-skid` is written as a consumer writes it: through `import fransys as
fr`. An import of any `fransys_*` package would make it a design only we can write.
"""

import ast
import sys
from pathlib import Path

SKID = Path(__file__).resolve().parent.parent / "examples" / "demo-skid"
ALLOWED = {"fransys", *sys.stdlib_module_names}


def foreign_imports(source: str) -> set[str]:
    """The top-level module names `source` imports that are neither `fransys` nor the stdlib."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add((node.module or "").split(".")[0])
    return names - ALLOWED


def test_the_skid_has_a_design_module():
    assert (SKID / "skid.py").is_file()


def test_the_skid_imports_only_fransys_and_the_stdlib():
    for path in sorted(SKID.glob("*.py")):
        assert foreign_imports(path.read_text(encoding="utf-8")) == set(), path.name


def test_the_check_names_a_workspace_package_import():
    assert foreign_imports("import fransys_model\nfrom fransys_layout.engines import x") == {
        "fransys_model",
        "fransys_layout",
    }
    assert (
        foreign_imports("import fransys as fr\nfrom fransys.colours import BK\nimport math")
        == set()
    )
