"""A `freeze` that adds the drawing library record the facade writes (GRID-HOME G6).

The tests build models without the facade; `derive` reads the grid from the record, so a model
needs one. The numbers are this test package's own copy of the bundled library's.
"""

import tomllib
from decimal import Decimal
from pathlib import Path

from fransys_model.kernel import Draft, Model, Origin, Record, evolve, make_id
from fransys_model.kernel import freeze as kernel_freeze
from fransys_model.layout import (
    DrawingLibrary,
    PaperChoice,
    a2_sheet_format,
    colour_codes,
    default_sheet_format,
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
from fransys_model.vocab import PageKind

_KEY = ("test", "library")
_EM = Decimal(2048)
_ORIGIN = Origin(file="pdf_library.py", line=0, note="test library")


def drawing_library(divisions: int = 8) -> DrawingLibrary:
    """The record with the bundled library's numbers."""
    return DrawingLibrary(
        id=make_id(DrawingLibrary, _KEY),
        key=_KEY,
        module_mm=Decimal("2.5"),
        divisions=divisions,
        wire_pitch=8,
        wire_pitch_fine=4,
        font_family="DejaVu Sans",
        ascent_ratio=Decimal(1556) / _EM,
        descent_ratio=Decimal(426) / _EM,
        ems=frozendict(
            {
                h: Decimal(h) * _EM / 1493
                for h in ("1", "1.8", "2", "2.2", "2.5", "3", "3.2", "3.5", "4", "5", "6")
            }
        ),
        lines=frozendict(
            {"normal": Decimal("0.25"), "thick": Decimal("0.5"), "rule": Decimal("0.18")}
        ),
        heights=frozendict(
            {
                "smallest": Decimal("1.8"),
                "body": Decimal("2.5"),
                "heading_2": Decimal("3.5"),
                "heading_1": Decimal(5),
            }
        ),
    )


def paper_records() -> tuple[Record, Record, PaperChoice]:
    """The paper records the facade writes: A3 by default, the block diagram on A2 (stock)."""
    a3, a2 = default_sheet_format(), a2_sheet_format()
    key = ("test", "paper")
    by_kind = frozendict({PageKind.BLOCK_DIAGRAM.value: a2.id})
    return (
        a3,
        a2,
        PaperChoice(id=make_id(PaperChoice, key), key=key, default=a3.id, by_kind=by_kind),
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


def with_library(model: Model, divisions: int = 8) -> Model:
    """`model` with the record."""
    return evolve(
        model, put=(drawing_library(divisions), *paper_records(), *house_records()), origin=_ORIGIN
    )


def freeze(draft: Draft) -> Model:
    """`draft` frozen, with the record."""
    return with_library(kernel_freeze(draft))
