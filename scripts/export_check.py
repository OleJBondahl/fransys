"""The release's export check (spec EXPORT-CHECK): four parts, one process each, stopping at the first red.

a imports every surface module, b collects every test, c runs the tests that read the whole tree, d lints
scripts and runs the hard lean check. A red names its part and exits 13.
"""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORT_ALL = (
    "import importlib, sys; sys.path.insert(0, 'scripts'); import lean_surface as s; [importlib.import_module(m) for m in s.surface_modules()]"
)


def _names(tree: ast.Module) -> set[str]:
    """Every module and imported name the file's import statements mention."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found |= {node.module or "", *(a.name for a in node.names)}
        elif isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
    return {n.split(".")[-1] for n in found}


def _lists_root(tree: ast.Module) -> bool:
    """True when the file globs, iterates or walks the repo ROOT itself."""
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    return any(f.attr in {"glob", "rglob", "iterdir"} and ast.unparse(f.value).endswith("ROOT") for f in calls)


def whole_tree_tests() -> list[str]:
    """Test files that import gate_scan or tracked (through any helper), or list ROOT themselves."""
    files = sorted({*ROOT.glob("tests/**/*.py"), *ROOT.glob("packages/*/tests/**/*.py")})
    trees = {p: ast.parse(p.read_text(encoding="utf-8")) for p in files}
    hit = {p.stem for p, t in trees.items() if _lists_root(t) or _names(t) & {"gate_scan", "tracked"}}
    while grown := {p.stem for p, t in trees.items() if p.stem not in hit and _names(t) & hit}:
        hit |= grown
    return [str(p.relative_to(ROOT)) for p in files if p.stem in hit and p.name.startswith("test_")]


def parts() -> list[tuple[str, list[list[str]]]]:
    """Each part's letter and name with its commands."""
    uv, pytest = ["uv", "run"], ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"]
    return [
        ("a imports", [[*uv, "python", "-c", IMPORT_ALL]]),
        ("b collect", [[*pytest, "--collect-only"]]),
        ("c whole-tree readers", [[*pytest, *whole_tree_tests()]]),
        ("d ruff scripts and lean hard", [[*uv, "ruff", "check", "scripts/"], [*uv, "python", "scripts/lean_check.py", "hard"]]),
    ]


def main() -> int:
    for name, commands in parts():
        for command in commands:
            if subprocess.run(command, cwd=ROOT, check=False).returncode != 0:  # noqa: S603  fixed argument lists
                sys.stdout.write(f"EXPORT CHECK RED: part {name}\n")
                return 13
        sys.stdout.write(f"export check part {name}: ok\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
