"""Overview engine, reading: the model's overview view rows to the facts of every view.

The only place, with `write/`, where the overview engine meets the model vocabulary.
"""

from typing import Any

from fransys_layout.engines.diagram.read.readings import readings
from fransys_layout.engines.overview.read.facts import view_facts
from fransys_layout.engines.overview.read.lanes import lane_plan
from fransys_layout.engines.overview.read.values import BoxSpec, LineSpec, box_ident
from fransys_model.derive import overview_view_rows
from fransys_model.layout import BoxKey, OverviewMode
lazy from fransys_layout.engines.overview.read.values import ViewFacts
lazy from fransys_model.derive import ViewBox, ViewLine, ViewRows
lazy from fransys_model.kernel import Id, Model

__all__ = ("BoxKey", "read_views")


def _box(box: ViewBox) -> BoxSpec:
    return BoxSpec(box=box_ident(box.key), key=box.key, lines=box.lines, dashed=box.dashed)


def _carrier(line: ViewLine, index: int) -> Id[Any]:
    """The ident a line is placed under: its cable, else one made from its place in the view."""
    return line.via if line.via is not None else Id(kind="line", value=f"{line.kind}-{index}")


def _line(line: ViewLine, index: int) -> LineSpec:
    return LineSpec(
        carrier=_carrier(line, index),
        a=box_ident(line.a),
        b=box_ident(line.b),
        kind=line.kind,
        via=line.via,
        strip=line.strip,
        text=line.text,
        tab_a=line.tab_a,
        tab_b=line.tab_b,
    )


def _facts(model: Model, rows: ViewRows) -> ViewFacts:
    specs = (
        tuple(_box(b) for b in rows.boxes),
        tuple(_line(line, n) for n, line in enumerate(rows.lines)),
    )
    unit = rows.unit
    plan = lane_plan(model, unit, rows) if rows.mode is OverviewMode.LANES and unit else ((), ())
    return view_facts(model, (rows.unit, rows.level, rows.mode), rows.open, specs, plan)


def read_views(model: Model) -> tuple[ViewFacts, ...]:
    """Every view: the system level, then each unit's plain level, its strips and its folds."""
    return tuple(
        _facts(model, rows) for unit in readings(model) for rows in overview_view_rows(model, unit)
    )
