"""JSON form of recorded `grid_path` calls: `(start, goal, field, path)` in, tuples out."""

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages.grid_path import Field
from fransys_layout.stages.space import End, Lane, Obstacle

type Call = tuple[End, End, Field, tuple[Point, ...] | None]


def _box(b: Box) -> list[int]:
    return [b.x, b.y, b.width, b.height]


def _end(e: End) -> list:
    return [e.at.x, e.at.y, e.facing.value]


def encode(call: Call) -> dict:
    """One call as plain JSON values; sets are sorted so the output is stable."""
    start, goal, f, path = call
    return {
        "start": _end(start),
        "goal": _end(goal),
        "region": _box(f.region),
        "obstacles": [
            [_box(o.box), [[_end(lane.end), _box(lane.extent)] for lane in o.lanes]]
            for o in f.obstacles
        ],
        "free": sorted(f.free),
        "busy": sorted(f.busy),
        "turn": f.turn_penalty,
        "crossing": f.crossing_penalty,
        "axes": [[x, y, "".join(sorted(a))] for (x, y), a in sorted(f.axes.items())],
        "path": None if path is None else [[p.x, p.y] for p in path],
    }


def _box_of(raw: list[int]) -> Box:
    return Box(x=raw[0], y=raw[1], width=raw[2], height=raw[3])


def _decode_end(e: list) -> End:
    return End(at=Point(x=e[0], y=e[1]), facing=Facing(e[2]))


def decode(raw: dict) -> Call:
    """The inverse of `encode`."""
    field = Field(
        region=_box_of(raw["region"]),
        obstacles=tuple(
            Obstacle(
                box=_box_of(box),
                lanes=tuple(Lane(end=_decode_end(e), extent=_box_of(ext)) for e, ext in lanes),
            )
            for box, lanes in raw["obstacles"]
        ),
        free=frozenset(map(tuple, raw["free"])),
        busy=frozenset(map(tuple, raw["busy"])),
        turn_penalty=raw["turn"],
        crossing_penalty=raw["crossing"],
        axes={(x, y): frozenset(a) for x, y, a in raw["axes"]},
    )
    path = None if raw["path"] is None else tuple(Point(x=x, y=y) for x, y in raw["path"])
    return _decode_end(raw["start"]), _decode_end(raw["goal"]), field, path
