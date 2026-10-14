"""Private to `write/`: the records of one placed view, keyed by its unit and open strip."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import AuthoringKey, Id, make_id
from fransys_model.layout import (
    BoxKey,
    OverviewBox,
    OverviewLine,
    OverviewTab,
    OverviewView,
    RoutePoint,
    box_key,
    line_key,
    view_key,
)
lazy from fransys_layout.lint._diagram_scene import Scene

if TYPE_CHECKING:
    from fransys_layout.engines.diagram.values import PlacedBox, PlacedSheet
    from fransys_layout.engines.overview.read.values import BoxSpec, LineSpec, ViewFacts


@dataclass(frozen=True)
class _Ctx:
    """What every record of one view shares: its key and id, the stamp and the box tokens."""

    key: AuthoringKey
    view: Id[Any]
    stamp: str
    keys: dict[Id[Any], BoxKey]

    def box_key(self, box: Id[Any]) -> AuthoringKey:
        return box_key(self.key, self.keys[box])


def _tabs(placed: PlacedBox, scene: Scene) -> tuple[OverviewTab, ...]:
    """The tabs outside the box edge, in the order placed, as the lint scene measured them."""
    rects = next(b.tabs for b in scene.boxes if b.box == placed.box)
    return tuple(
        OverviewTab(index=i, x=r.x, y=r.y, text_width=t.text_width)
        for i, (r, t) in enumerate(zip(rects, placed.tabs, strict=True))
    )


def _box(spec: BoxSpec, placed: PlacedBox, scene: Scene, ctx: _Ctx) -> OverviewBox:
    key = ctx.box_key(spec.box)
    return OverviewBox(
        id=make_id(OverviewBox, key),
        key=key,
        view=ctx.view,
        ref=spec.key.ref,
        stub_of=None
        if spec.key.at is None
        else make_id(OverviewBox, box_key(ctx.key, BoxKey(ref=spec.key.at))),
        dashed=placed.dashed,
        x=placed.x,
        y=placed.y,
        width=placed.width,
        height=placed.height,
        tabs=_tabs(placed, scene),
        produced_by=ctx.stamp,
    )


def _line(spec: LineSpec, sheet: PlacedSheet, ctx: _Ctx) -> OverviewLine:
    placed = next(p for p in sheet.lines if (p.cable, p.a, p.b) == (spec.carrier, spec.a, spec.b))
    ends = (ctx.keys[spec.a], ctx.keys[spec.b])
    key = line_key(ctx.key, spec.kind, ends, (spec.via, spec.strip))
    return OverviewLine(
        id=make_id(OverviewLine, key),
        key=key,
        view=ctx.view,
        a=make_id(OverviewBox, ctx.box_key(spec.a)),
        b=make_id(OverviewBox, ctx.box_key(spec.b)),
        kind=spec.kind,
        via=spec.via,
        strip=spec.strip,
        points=tuple(RoutePoint(index=i, x=p.x, y=p.y) for i, p in enumerate(placed.points)),
        text_x=placed.text_x,
        text_y=placed.text_y,
        produced_by=ctx.stamp,
    )


def view_records(facts: ViewFacts, sheet: PlacedSheet, scene: Scene, stamp: str) -> tuple[Any, ...]:
    """The `OverviewView`, its boxes and its lines.

    A lanes view holds its lane texts in `ext["lane_heads"]`: a `(group node, x, y)` per lane.
    """
    key = view_key(facts.unit, facts.level, facts.mode, facts.open)
    view = make_id(OverviewView, key)
    ctx = _Ctx(key=key, view=view, stamp=stamp, keys={b.box: b.key for b in facts.boxes})
    head = OverviewView(
        id=view,
        key=key,
        unit=facts.unit,
        level=facts.level,
        mode=facts.mode,
        open=facts.open,
        open_at=None,
        produced_by=stamp,
        ext=frozendict({"lane_heads": tuple((t.owner, t.x, t.y) for t in sheet.texts)})
        if sheet.texts
        else frozendict(),
    )
    placed = {p.box: p for p in sheet.boxes}
    return (
        head,
        *(_box(b, placed[b.box], scene, ctx) for b in facts.boxes),
        *(_line(ln, sheet, ctx) for ln in facts.lines),
    )
