"""Write `_version.py` from `pyproject.toml`'s version.

`tests/test_version.py` fails while they differ.

`just build-electrical-symbols` runs it, then `symdef build` writes `build/` and `bundle.json`.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYPROJECT = ROOT / "pyproject.toml"
VERSION_MODULE = ROOT / "src" / "electrical_symbols" / "_version.py"


def project_version(pyproject_text: str) -> str:
    """Return `[project].version` of a `pyproject.toml`'s text."""
    return tomllib.loads(pyproject_text)["project"]["version"]


def version_module(version: str) -> str:
    """Return the text of `_version.py` for `version`."""
    return (
        '"""The package version, written by scripts/write_version.py. Do not edit."""\n'
        "\n"
        f'LIBRARY_VERSION = "{version}"\n'
    )


def main() -> None:
    """Write `_version.py`."""
    version = project_version(PYPROJECT.read_text(encoding="utf-8"))
    VERSION_MODULE.write_text(version_module(version), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
