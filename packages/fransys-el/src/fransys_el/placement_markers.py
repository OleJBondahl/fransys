"""The box of each lone stub, fitted to its text before placement (R318, MARKER-ANCHORS).

A stub or a copy is a marker symbol; symdef measures it once the text it will print is fitted into
its slot, and the core reserves that box. A text that fits the plain marker adds nothing.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, cast

from electrical_symbols import MARKER_FACING
from fransys_model.derive import far_pins, stub_far, stub_text_at

from .placement_ids import pin_names, symbol_ids
from .placement_views import marker_boxes
from .write_stubs import stub_ends

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import Box, Orientation, PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port, Unit

    from .placement_kit import SymbolKit

__all__ = ["ARROW", "KINDS", "LONE", "facing_views", "pin_ports", "stub_fit"]

#: The reference kind whose box is fitted to the widest line it can print (R350).
ARROW = "arrow"

#: The reference kinds that have one end: each is an off stub, its box fitted to its text.
LONE = ("stub", "copy")

#: Every reference kind; a kind with no fitted symbol of its own gets the plain marker's box.
KINDS = ("tag", "arrow", "star", *LONE)

type Fit = Mapping[tuple[PinRef, str], Mapping[Orientation, Box]]
type StubLines = Mapping[tuple[PinRef, PinRef], tuple[int, ...]]
type StubTable = Mapping[tuple[int, int], Mapping[Orientation, Box]]


def facing_views() -> tuple[frozenset[Orientation], Orientation, Orientation]:
    """The marker views that lie above or below a pin, the one above and the one below."""
    up, down = (cast("Orientation", MARKER_FACING[side]) for side in "NS")
    mirrored = cast("Orientation", f"M{up}"), cast("Orientation", f"M{down}")
    return frozenset([up, down, *mirrored]), up, down


def pin_ports(model: Model, kit: SymbolKit) -> dict[PinRef, list[Id[Port]]]:
    """Every model port that each symbol pin draws."""
    found: dict[PinRef, list[Id[Port]]] = defaultdict(list)
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        found[pin].append(port)
    return found


def _texts(model: Model, unit: Id[Unit] | None, ports: Sequence[Id[Port]]) -> list[str]:
    """The one text a stub at `ports` prints: a line for each conductor that leaves."""
    reach = far_pins(model, ports)
    fars = list(dict.fromkeys(far for _, far in reach))
    ends = [end for far in fars for end in stub_far(model, ports, [far])] if reach else stub_far(model, ports)[:1]
    lines = [stub_text_at(model, unit, end, north=False) for end in ends]
    return ["\n".join(lines)] if lines else []


def _lines(
    model: Model, unit: Id[Unit] | None, ports: Mapping[PinRef, list[Id[Port]]], pins: Iterable[PinRef]
) -> dict[tuple[PinRef, PinRef], list[str]]:
    """The line each conductor from a pin of `pins` to a far pin prints, by (near pin, far pin): placement does not change it (R1597)."""
    pin_of = {port: pin for pin, names in ports.items() for port in names}
    found: dict[tuple[PinRef, PinRef], list[str]] = {}
    for near in set(pins):
        for far in dict.fromkeys(pin_of[f] for _, f in far_pins(model, ports.get(near, ())) if f in pin_of):
            found[near, far] = [stub_text_at(model, unit, end, north=False) for end in stub_ends(model, ports[near], ports[far])]
    return found


def _sharing(texts: Mapping[tuple[PinRef, PinRef], list[str]]) -> list[set[PinRef]]:
    """The groups of near pins that share a far symbol, joined where they share another: the pins a merged stub can stand for (a bundle, R1319)."""
    groups: list[set[PinRef]] = []
    for far in {f.sym for _, f in texts}:
        joined = {n for n, f in texts if f.sym == far}
        for g in [g for g in groups if g & joined]:
            groups.remove(g)
            joined |= g
        groups.append(joined)
    return groups


def _sized(
    library: Library, texts: Mapping[tuple[PinRef, PinRef], list[str]], pins: list[PinRef], stands: Iterable[Sequence[PinRef]]
) -> tuple[dict[str, Mapping[Orientation, Box]], StubLines, StubTable]:
    """Each line text's box, each conductor's line width, and the box by (widest width, line count) up to the count a stub can reach."""
    fits = {text: marker_boxes(library, text) for lines in texts.values() for text in lines}
    widths = {text: box["R90"].h for text, box in fits.items()}
    lines = frozendict({k: tuple(widths[t] for t in v) for k, v in texts.items() if v})
    sample = {w: t for t, w in widths.items()}
    own = {p: [t for (n, _), v in texts.items() if n == p for t in v] for p in set(pins)}
    reach = max((sum(len(own.get(p, ())) for p in g) for g in (*_sharing(texts), *stands)), default=0)
    table = frozendict({(w, n): marker_boxes(library, "\n".join([t] * n)) for w, t in sample.items() for n in range(1, reach + 1)})
    return fits, lines, table


def stub_fit(
    model: Model,
    kit: SymbolKit,
    unit_library: tuple[Id[Unit] | None, Library],
    pins: Iterable[PinRef],
    stands: Iterable[Sequence[PinRef]] = (),
) -> tuple[Fit, StubLines, StubTable]:
    """The core's marker sizes (R1597): each kind's box at a pin, each conductor's line width, and the box by (widest width, line count).

    `Fit` is the pin's own text, the bound before the ledger exists; a line's width is its one-line turned box along the wire.
    """
    unit, library = unit_library
    ports = pin_ports(model, kit)
    plain = marker_boxes(library)
    pins = list(pins)
    fits, lines, table = _sized(library, _lines(model, unit, ports, pins), pins, stands)
    found = {}
    for pin in set(pins):
        pin_text = _texts(model, unit, ports[pin]) if pin in ports else []
        if pin_text:
            fits[pin_text[0]] = fits.get(pin_text[0]) or marker_boxes(library, pin_text[0])
            found.update({(pin, kind): fits[pin_text[0]] if kind in LONE else plain for kind in KINDS if kind != ARROW})
    return frozendict(found), lines, table
