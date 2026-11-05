"""The house text records for author tests that run a derive function or a check on a bare model.

The facade writes these records; an author test freezes without it. The builders are the model's
own and the values are `settings.toml`'s (SETTINGS-OPEN R477 item 5).
"""

import tomllib
from pathlib import Path

from fransys_model.kernel import Model, Origin, Record, evolve
from fransys_model.layout import house_records as house_records_of


def house_records() -> tuple[Record, ...]:
    """The house text records of `settings.toml`, built by the model's builders."""
    path = Path(__file__).parents[2] / "fransys" / "src" / "fransys" / "settings.toml"
    t = tomllib.loads(path.read_text(encoding="utf-8"))
    t["profile"] = tomllib.loads(path.parents[3].joinpath("fransys-layout/src/fransys_layout/layout.toml").read_text(encoding="utf-8"))["profile"]
    return house_records_of(t)


def with_house(model: Model) -> Model:
    """`model` with the house text records only."""
    origin = Origin(file="author_library.py", line=0, note="test house records")
    return evolve(model, put=house_records(), origin=origin)
