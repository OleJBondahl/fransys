"""The workspace root, found from any test file, also from mutmut's deeper `mutants/` copy."""

from pathlib import Path


def _is_workspace(folder: Path) -> bool:
    pyproject = folder / "pyproject.toml"
    return pyproject.is_file() and "[tool.uv.workspace]" in pyproject.read_text(encoding="utf-8")


WORKSPACE_ROOT = next(p for p in Path(__file__).resolve().parents if _is_workspace(p))
