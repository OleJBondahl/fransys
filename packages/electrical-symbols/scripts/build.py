"""Regenerate the tracked build: `build/`, `bundle.json` and `_version.py`.

`_version.py` holds `pyproject.toml`'s version; `tests/test_version.py` fails while they differ.
"""

import shutil
import sys
import tomllib
from pathlib import Path

from graphical_symbols import load_library, stale_build, write_build

ROOT = Path(__file__).parent.parent
PYPROJECT = ROOT / "pyproject.toml"
VERSION_MODULE = ROOT / "src" / "electrical_symbols" / "_version.py"
# The toolkit names the bundle's package after the standard ("IEC 60617" gives `iec60617`) and has
# no setting to change that (T1, D39). The package here is `electrical_symbols`, so the bundle is
# moved after the write; the toolkit's own path is then removed with its contents (a leftover
# `__pycache__` from the old package name must not make reruns fail) and `stale_build` reports it.
TOOLKIT_BUNDLE = ROOT / "src" / "iec60617" / "bundle.json"
PACKAGE_BUNDLE = ROOT / "src" / "electrical_symbols" / "bundle.json"


def project_version(pyproject_text: str) -> str:
    """Return `[project].version` of a `pyproject.toml`'s text."""
    return tomllib.loads(pyproject_text)["project"]["version"]


def version_module(version: str) -> str:
    """Return the text of `_version.py` for `version`."""
    return (
        '"""The package version, written by scripts/build.py. Do not edit."""\n'
        "\n"
        f'LIBRARY_VERSION = "{version}"\n'
    )


def main() -> None:
    """Write the build, move the bundle into the package, delete what only an old build wrote."""
    version = project_version(PYPROJECT.read_text(encoding="utf-8"))
    VERSION_MODULE.write_text(version_module(version), encoding="utf-8", newline="\n")
    library = load_library(ROOT)
    written = write_build(library, ROOT)
    TOOLKIT_BUNDLE.replace(PACKAGE_BUNDLE)
    shutil.rmtree(TOOLKIT_BUNDLE.parent)
    removed = [path for path in stale_build(library, ROOT) if path != TOOLKIT_BUNDLE]
    for path in removed:
        path.unlink()
    sys.stdout.write(
        f"build: {len(written)} files written, {len(removed)} removed, version {version}\n"
    )


if __name__ == "__main__":
    main()
