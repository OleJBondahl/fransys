"""The package's one read of `bundle.json`; `__init__` and `natural` import LIBRARY from here."""

from pathlib import Path

from symdef import Library, load_bundle

LIBRARY: Library = load_bundle(Path(__file__).with_name("bundle.json"))
