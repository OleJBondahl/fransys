"""The house text records for author tests that run a derive function or a check on a bare model.

The facade writes these records; an author test freezes without it. The builders are the model's
own and the values are `settings.toml`'s (SETTINGS-OPEN R477 item 5).
"""

import tomllib
from pathlib import Path

from fransys_model.kernel import Model, Origin, Record, evolve
from fransys_model.layout import (
    colour_codes,
    frame_form,
    harness_text,
    reference_text,
    revision_form,
    revision_table_form,
    stub_text,
    title_block_form,
    wire_label_text,
    words,
)


def house_records() -> tuple[Record, ...]:
    """The house text records of `settings.toml`, built by the model's builders."""
    path = Path(__file__).parents[2] / "fransys" / "src" / "fransys" / "settings.toml"
    t = tomllib.loads(path.read_text(encoding="utf-8"))
    return (
        reference_text(**t["reference"]),
        frame_form(**t["frame"]),
        stub_text(**t["stub"]),
        wire_label_text(**t["wire_label"]),
        harness_text(**t["harness"]),
        colour_codes(**t["colours"]),
        title_block_form(**t["title_block"]),
        revision_table_form(**t["revision_table"]),
        revision_form(
            date_format=t["revision"]["date_format"],
            initials_required=t["revision"]["initials_required"],
            printed=t["revision"]["format"],
        ),
        words(t["words"]),
    )


def with_house(model: Model) -> Model:
    """`model` with the house text records only."""
    origin = Origin(file="author_library.py", line=0, note="test house records")
    return evolve(model, put=house_records(), origin=origin)
