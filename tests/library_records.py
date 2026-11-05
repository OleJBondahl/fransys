"""The drawing library, paper and house records the facade writes, as one test-side copy (GRID-HOME G6).

The tests build models without the facade; `derive` reads the grid from the record, so a model
needs them. The numbers are the bundled library's, the house texts are `settings.toml`'s.
"""

import random
import tomllib
from decimal import Decimal
from pathlib import Path

from fransys_model.kernel import Draft, Model, Origin, Record, evolve, make_id
from fransys_model.kernel import freeze as kernel_freeze
from fransys_model.layout import DrawingLibrary, PaperChoice, a2_sheet_format, default_sheet_format
from fransys_model.layout import house_records as house_records_of
from fransys_model.vocab import PageKind

_KEY = ("test", "library")
_EM = Decimal(2048)
_ORIGIN = Origin(file="library_records.py", line=0, note="test library")


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
        ems=frozendict({h: Decimal(h) * _EM / 1493 for h in ("1", "1.8", "2", "2.2", "2.5", "3", "3.2", "3.5", "4", "5", "6")}),
        lines=frozendict({"normal": Decimal("0.25"), "thick": Decimal("0.5"), "rule": Decimal("0.18")}),
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
    path = Path(__file__).parents[1] / "packages" / "fransys" / "src" / "fransys" / "settings.toml"
    t = tomllib.loads(path.read_text(encoding="utf-8"))
    layout_toml = path.parents[3] / "fransys-layout" / "src" / "fransys_layout" / "layout.toml"
    t["profile"] = tomllib.loads(layout_toml.read_text(encoding="utf-8"))["profile"]
    return house_records_of(t)


def with_library(model: Model, divisions: int = 8) -> Model:
    """`model` with the record."""
    return evolve(model, put=(drawing_library(divisions), *paper_records(), *house_records()), origin=_ORIGIN)


def freeze(draft: Draft) -> Model:
    """`draft` frozen, with the record."""
    return with_library(kernel_freeze(draft))


def shuffled_draft(records: list[Record], origin: Origin, seed: int | None = None) -> Draft:
    """`records` in a `Draft`, shuffled by `seed` when there is one."""
    records = list(records)
    if seed is not None:
        random.Random(seed).shuffle(records)  # noqa: S311 -- a test shuffle, not security
    draft = Draft()
    draft.extend(records, origin=origin)
    return draft
