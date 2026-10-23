"""The house conventions a placement test builds: `layout.toml`'s table, read as the facade does."""

import tomllib
from dataclasses import replace
from pathlib import Path

from fransys_el import Conventions, house_conventions

import fransys_layout
from electrical_symbols import LIBRARY

LAYOUT = tomllib.loads(
    (Path(fransys_layout.__file__).parent / "layout.toml").read_text(encoding="utf-8")
)["layout"]


def house() -> Conventions:
    """The house conventions of the stock library and `layout.toml`."""
    return house_conventions(LAYOUT, LIBRARY)


def tables_on() -> Conventions:
    """The house conventions with `contact_tables` on (CONTACT-TABLE): table annexes are built."""
    return replace(house(), contact_tables=True)
