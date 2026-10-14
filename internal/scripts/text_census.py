"""Text census: count the texts a build loses, by kind and by cause, as markdown tables.

Runs against an INSTALLED fransys: the public API plus the installed packages, no repo files.
It wraps the text placer and the engine's stage runs, builds the design, and prints the tables.

    uv run --with "fransys @ git+https://github.com/OleJBondahl/fransys@v0.18.4#subdirectory=packages/fransys" \
        python text_census.py DESIGN.py [--text-height MM ...] [--label NAME]

DESIGN.py defines `d` (the design, `fr.design(...)`) and optionally `documents` (a tuple); it is
built as `fr.build(d, *documents)`. Its folder goes on `sys.path`, so it can import its parts.
`--text-height` repeats: the design is authored again under each height.

A cause is `order` when some candidate of an unplaced text was blocked only by texts placed
earlier in the call (another order could free it), else `no_room`. A loss is `used` when its
page comes from the stage run that reaches the output (and its finding is there), `unused` when
the page is spliced out for another run's (`profiles.lay_out`), `replaced` when a second
`clear_bodies` call re-placed the page, and `leak` when it is used and the build lacks its finding.
It reads private placer names, so it is pinned to the version it runs against.
"""  # noqa: E501 - the install command is one line

import argparse
import importlib
import json
import runpy
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys
import fransys_author.design as design_mod

from fransys_layout.engines.schematic import engine, profiles
from fransys_layout.engines.schematic.read.profile_runs import finding_unit
from fransys_layout.geometry import overlaps
from fransys_layout.stages.space import Space, covers, crosses
from fransys_layout.stages.texts import place_texts as pt

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fransys_layout.stages.texts.candidates import TextTable
    from fransys_layout.stages.texts.place_texts import PlacedText, TextToPlace

CODES = ("LABEL_UNPLACED", "TEXT_OVERLAP", "WIRE_OVER_LABEL", "TEXT_CROSSED_BY_ROUTE")
CALLERS = (
    "fransys_layout.engines.schematic._line_drawn",
    "fransys_layout.stages.labels",
    "fransys_layout.stages.texts.clear_bodies",
    "fransys_layout.stages.texts.power",
)
type Record = dict[str, Any]
STATE: dict[str, Any] = {"build": 0, "run": 0, "plan": 0, "mm": None, "label": ""}
RECORDS: list[Record] = []
UNDO: list[tuple[object, str, object]] = []
# The placer's own helpers: its candidate list per text, its sort key and its lane run.
_key, _options, _run = pt._key, pt._options, pt._run  # noqa: SLF001 - the census reads the placer's own rules
_USED = ("used", "leak")


@dataclass(frozen=True)
class Call:
    """What one `place_texts` call was given."""

    texts: Sequence[TextToPlace]
    space: Space
    table: TextTable
    lanes: Sequence
    runs: Sequence


def _blockers(text: TextToPlace, call: Call, earlier: list, stubs: list) -> list[list[str]]:
    """Per candidate of an unplaced text, the classes of what blocked it."""
    out = []
    foreign = [b for (_, h, b) in earlier if h != text.handle]
    for place, fits in _options(text, call.table):
        reasons: set[str] = set() if fits else {"anchor_unfit"}
        box = place.box
        if any(overlaps(part, other) for part in place.stub for other in foreign):
            reasons.add("stub_on_text")
        if not call.space.holds(box):
            reasons.add("content_edge")
        for shape in call.space.shapes:
            if shape.owner not in text.own and overlaps(box, shape.box):
                reasons.add("symbol_or_keepout" if shape.owner is not None else "marker_or_box")
        reasons.update(f"text:{k.value}" for k, _, b in earlier if overlaps(box, b))
        if any(h != text.handle and overlaps(box, b) for h, b in stubs):
            reasons.add("stub")
        if box.width > 0 and box.height > 0 and any(covers(box, _run(x.box)) for x in call.lanes):
            reasons.add("lane")
        if any(crosses(box, run) for run in call.runs):
            reasons.add("run")
        out.append(sorted(reasons))
    return out


def _classify(call: Call, placed: Sequence[PlacedText]) -> list[Record]:
    """Per unplaced text: the blocker classes of each candidate, and the cause."""
    out: list[Record] = []
    earlier: list = []
    stubs: list = []
    ordered = sorted(call.texts, key=lambda one: _key(one, call.table))
    for text, done in zip(ordered, placed, strict=True):
        if done.unplaced:
            reasons = _blockers(text, call, earlier, stubs)
            soft = [
                bool(r) and all(x.startswith("text:") or x in ("stub", "stub_on_text") for x in r)
                for r in reasons
            ]
            out.append(
                {
                    "kind": text.kind.value,
                    "handle": str(text.handle),
                    "n_candidates": len(reasons),
                    "reasons": reasons,
                    "cause": "order" if any(soft) else "no_room",
                }
            )
        stubs.extend((text.handle, b) for b in _options(text, call.table)[done.index][0].stub)
        earlier.append((done.kind, done.handle, done.box))
    return out


def _place_record(caller: str, call: Call, placed: Sequence[PlacedText]) -> Record:
    index: dict[str, Counter] = defaultdict(Counter)
    for one in placed:
        index[one.kind.value][one.index] += 1
    return {
        "rec": "place",
        **{k: STATE[k] for k in ("build", "run", "plan")},
        "caller": caller,
        "n_texts": len(call.texts),
        "kinds": dict(Counter(t.kind.value for t in call.texts)),
        "indices": {k: dict(v) for k, v in index.items()},
        "unplaced": _classify(call, placed) if any(one.unplaced for one in placed) else [],
    }


def _patch(obj: object, name: str, new: object) -> None:
    """Replace `obj.name` with `new`; `uninstall` puts every original back."""
    UNDO.append((obj, name, getattr(obj, name)))
    setattr(obj, name, new)


def uninstall() -> None:
    """Undo `install` and `set_text_height`, newest first, and clear the records."""
    while UNDO:
        obj, name, was = UNDO.pop()
        setattr(obj, name, was)
    RECORDS.clear()
    STATE.update(build=0, run=0, plan=0, mm=None, label="")


def _keys(findings: Sequence) -> list[list]:
    return [[f.code, f.message, [str(s) for s in f.subjects]] for f in findings if f.code in CODES]


def _wrapped_place(orig: Callable) -> Callable:
    def place(texts, space, table, *, lanes=(), runs=()):  # noqa: ANN001, ANN202 - mirrors the placer's signature
        placed, findings = orig(texts, space, table, lanes=lanes, runs=runs)
        caller = sys._getframe(1).f_code.co_name  # noqa: SLF001 - the calling stage names the call
        RECORDS.append(_place_record(caller, Call(texts, space, table, lanes, runs), placed))
        return placed, findings

    return place


def _wrapped_once(orig: Callable) -> Callable:
    def once(model, unit, **kw):  # noqa: ANN001, ANN003, ANN202 - mirrors the engine's per-profile run
        STATE.update(run=STATE["run"] + 1, plan=0)
        laid, found = orig(model, unit, **kw)
        mine = [f for f in found if f.code in CODES]
        owner = [finding_unit(model, f) for f in mine]
        RECORDS.append(
            {
                "rec": "run",
                "build": STATE["build"],
                "run": STATE["run"],
                "unit": None if unit is None else str(unit),
                "plans": STATE["plan"],
                "findings": _keys(mine),
                "units": [None if one is None else str(one) for one in owner],
            }
        )
        return laid, found

    return once


def install() -> None:
    """Wrap the placer in every module that imports it, the engine's stage runs and `fr.build`."""
    orig_pages, orig_splice, orig_build = engine.place_pages, profiles.spliced, fransys.build

    def pages(*a, **k):  # noqa: ANN002, ANN003, ANN202 - mirrors `place_pages`
        STATE["plan"] += 1
        return orig_pages(*a, **k)

    def splice(base, runs, ranks):  # noqa: ANN001, ANN202 - mirrors `spliced`
        units = [sorted(map(str, one)) for one, _ in runs]
        RECORDS.append({"rec": "splice", "build": STATE["build"], "units": units})
        return orig_splice(base, runs, ranks)

    def build(*a, **k):  # noqa: ANN002, ANN003, ANN202 - mirrors `fr.build`
        STATE.update(build=STATE["build"] + 1, run=0, plan=0)
        result = orig_build(*a, **k)
        RECORDS.append(
            {"rec": "build", "build": STATE["build"], "findings": _keys(result.findings)}
        )
        return result

    place = _wrapped_place(pt.place_texts)
    for module in (pt, *(importlib.import_module(name) for name in CALLERS)):
        _patch(module, "place_texts", place)
    _patch(engine, "_run_once", _wrapped_once(engine._run_once))  # noqa: SLF001 - the per-profile run
    _patch(engine, "place_pages", pages)
    _patch(profiles, "spliced", splice)
    _patch(fransys, "build", build)


def set_text_height(mm: str | None) -> None:
    """Make every build take text height `mm` (None: the profile's own)."""
    cls = next(c for c in vars(design_mod).values() if isinstance(c, type) and "profile" in vars(c))
    if not any(obj is cls and name == "profile" for obj, name, _ in UNDO):
        orig = cls.profile

        def profile(self, *a, **k):  # noqa: ANN001, ANN002, ANN003, ANN202 - mirrors `profile`
            if STATE["mm"] is not None:
                k["text_height_mm"] = Decimal(STATE["mm"])
            return orig(self, *a, **k)

        _patch(cls, "profile", profile)
    STATE["mm"] = mm


def _tail(places: list[Record]) -> list[Record]:
    """Mark a place call that a following call of the same page replaced (clear_bodies pairs)."""
    for prev, one in pairwise(places):
        pair = one["caller"] == prev["caller"] == "place_clear_of_bodies"
        if pair and one["n_texts"] == prev["n_texts"]:
            prev["replaced"] = True
    return places


def _used(spliced: list[list[str]], run: int, unit: str | None) -> bool:
    """Whether the pages a finding's `unit` owns come from stage run `run` (`profiles.lay_out`)."""
    if run == 1:
        return not any(unit in units for units in spliced)
    return run - 2 < len(spliced) and unit in spliced[run - 2]


class Census:
    """The records of one report, indexed: which stage run's pages reach the output."""

    def __init__(self, records: Sequence[Record]) -> None:
        """Index `records` by build and run."""
        self.builds = {r["build"]: r for r in records if r["rec"] == "build"}
        self.runs = {(r["build"], r["run"]): r for r in records if r["rec"] == "run"}
        self.splices = {r["build"]: r["units"] for r in records if r["rec"] == "splice"}
        self.places = _tail([r for r in records if r["rec"] == "place"])

    def fates(self, run: Record) -> list[tuple[list, str]]:
        """Each LABEL_UNPLACED finding of a stage run with its fate: used, unused or leak."""
        out = Counter(json.dumps(f) for f in self.builds[run["build"]]["findings"])
        spliced = self.splices.get(run["build"], [])
        fates = []
        for f, unit in zip(run["findings"], run["units"], strict=True):
            key = json.dumps(f)
            if f[0] != "LABEL_UNPLACED":
                continue
            if not _used(spliced, run["run"], unit):
                fates.append((f, "unused"))
            elif out[key] > 0:
                out[key] -= 1
                fates.append((f, "used"))
            else:
                fates.append((f, "leak"))
        return fates

    def status(self, place: Record, lost: Record) -> str:
        """`replaced` by a re-call, else the fate of the text's finding, else `no finding`."""
        if place.get("replaced"):
            return "replaced"
        run = self.runs.get((place["build"], place["run"]))
        for f, fate in self.fates(run) if run else ():
            if lost["handle"] in f[2]:
                return fate
        return "no finding"


def _row(*cells: object) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(title: str, head: tuple, rows: list[tuple], empty: tuple) -> list[str]:
    body = [_row(*r) for r in rows] or [_row(*empty)]
    return [f"### {title}", "", _row(*head), _row(*("---" for _ in head)), *body, ""]


def _kind_rows(places: list[Record]) -> list[tuple]:
    kinds: Counter = Counter()
    taken: dict[str, Counter] = defaultdict(Counter)
    for p in places:
        kinds.update(p["kinds"])
        for k, d in p["indices"].items():
            taken[k].update({int(i): n for i, n in d.items()})
    return [
        (k, n, taken[k][0], sum(taken[k].values()) - taken[k][0], max(taken[k]))
        for k, n in sorted(kinds.items())
    ]


def _loss_tables(census: Census) -> tuple[list[tuple], list[tuple]]:
    unplaced: Counter = Counter()
    blockers: dict[str, Counter] = defaultdict(Counter)
    for p in census.places:
        for u in p["unplaced"]:
            status = census.status(p, u)
            unplaced[(u["kind"], u["cause"], status, p["plan"])] += 1
            if status in _USED:
                for r in u["reasons"]:
                    blockers[u["kind"]].update([",".join(r) or "none"])
    return (
        [(*k, n) for k, n in sorted(unplaced.items(), key=str)],
        [(k, b, n) for k, c in sorted(blockers.items()) for b, n in c.most_common(8)],
    )


def _run_rows(census: Census) -> list[tuple]:
    rows = []
    for (bn, rn), r in sorted(census.runs.items()):
        fates = Counter(fate for _, fate in census.fates(r))
        counts = (fates["used"], fates["unused"], fates["leak"])
        rows.append((bn, rn, r["unit"] or "top", r["plans"], *counts))
    return rows


def report(records: Sequence[Record], title: str) -> str:
    """The markdown tables for the records of one build set."""
    census = Census(records)
    out = Counter(c for b in census.builds.values() for c, *_ in b["findings"])
    texts = sum(p["n_texts"] for p in census.places)
    lost, blocked = _loss_tables(census)
    count = (len(census.builds), len(census.places), texts, *(out[c] for c in CODES))
    head = ("builds", "place calls", "texts", *CODES)
    lines = [f"## {title}", ""]
    lines += _table("Builds and the findings they carry", head, [count], ())
    lines += _table(
        "Texts by kind and the candidate index each took (all calls)",
        ("kind", "texts", "index 0", "index 1+", "worst index"),
        _kind_rows(census.places),
        ("none", 0, 0, 0, 0),
    )
    lines += _table(
        "Unplaced texts (status: replaced, used, unused or leak; plan: place_pages count)",
        ("kind", "cause", "status", "plan", "texts"),
        lost,
        ("none", "", "", "", 0),
    )
    lines += _table(
        "What blocked the used losses (candidates per blocker set)",
        ("kind", "blockers", "candidates"),
        blocked,
        ("none", "", 0),
    )
    lines += _table(
        "Stage runs: each run's LABEL_UNPLACED findings by where its pages go",
        ("build", "run", "unit", "plans", "used", "unused (spliced out)", "leak"),
        _run_rows(census),
        ("none", "", "", 0, 0, 0, 0),
    )
    return "\n".join(lines)


def load(path: Path) -> dict[str, Any]:
    """Run the design file; its folder goes on `sys.path` for its parts. Its globals come back."""
    sys.path.insert(0, str(path.parent))
    return runpy.run_path(str(path))


def main(argv: Sequence[str] | None = None) -> None:
    """Build the design under each text height and print one set of tables per height."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("design", type=Path)
    ap.add_argument("--text-height", action="append", default=[], metavar="MM")
    ap.add_argument("--label", default="")
    args = ap.parse_args(argv)
    install()
    for mm in args.text_height or [None]:
        set_text_height(mm)
        scope = load(args.design.resolve())  # authored under this height
        STATE["label"] = args.label or args.design.stem
        start = len(RECORDS)
        fransys.build(scope["d"], *scope.get("documents", ()))
        title = f"{STATE['label']} at {mm or 'house'} mm text height"
        print(report(RECORDS[start:], title))  # noqa: T201 - CLI output


if __name__ == "__main__":
    main()
