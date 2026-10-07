"""Every public callable's signature and annotations resolve at runtime (no NameError).

An annotation that names a type imported only under TYPE_CHECKING breaks `inspect.signature`
consumers, `just api` and the guide examples; this checks each surface name and each public
method of each public class.
"""

import importlib
import inspect
import typing
from typing import Any, NamedTuple

import fransys as fr
import pytest

SURFACES = (
    "fransys",
    "fransys.colours",
    "fransys_model.kernel",
    "fransys_model.vocab",
    "fransys_model.layout",
    "fransys_model.derive",
    "fransys_model.derive.drawing_text",
    "fransys_model.derive.baseline",
    "fransys_model.derive.numbering_pins",
    "fransys_model.derive.cable_drawing",
)

#: symbols whose annotation names a type imported only under TYPE_CHECKING (strict xfail)
KNOWN_FAILURES: frozenset[str] = frozenset(
    {
        # `Record` names Id, AuthoringKey and Value, and kernel.ids/values import kernel.record
        # at runtime: a runtime import would close an import cycle (test_boundaries).
        "fransys_model.kernel.Record.id",
        "fransys_model.kernel.Record.key",
        "fransys_model.kernel.Record.ext",
    }
)
REASON = "resolves when Record or Id/AuthoringKey/Value leave the kernel.record import cycle"


def _callables() -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for dotted in SURFACES:
        module = importlib.import_module(dotted)
        for name in module.__all__:
            obj = getattr(module, name)
            if not callable(obj):
                continue
            found.append((f"{dotted}.{name}", obj))
            if inspect.isclass(obj):
                for member_name, member in vars(obj).items():
                    if member_name.startswith("_"):
                        continue
                    func = member.fget if isinstance(member, property) else member
                    if isinstance(func, (staticmethod, classmethod)):
                        func = func.__func__
                    if inspect.isfunction(func):
                        found.append((f"{dotted}.{name}.{member_name}", func))
    return found


def _param(symbol: str, obj: object) -> object:
    marks = [pytest.mark.xfail(reason=REASON, strict=True)] if symbol in KNOWN_FAILURES else []
    return pytest.param(obj, id=symbol, marks=marks)


def _public_methods(label: str, obj: object) -> list[tuple[str, object]]:
    """Each public bound method of a live object, labelled `label.name`."""
    return [
        (f"{label}.{name}", getattr(obj, name))
        for name in dir(type(obj))
        if not name.startswith("_") and inspect.isfunction(inspect.getattr_static(type(obj), name))
    ]


class _Io(NamedTuple):
    J1: Any


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _unit_board(u: Any) -> _Io:
    _UNIT_DESIGNS.append(u)
    return _Io(u.device("J1", "DEMO-CONN-2P", interface=True))


_UNIT_DESIGNS: list[Any] = []


def _live() -> list[tuple[str, object]]:
    """The design, a unit body's design, and the handles a public call returns."""
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(_unit_board, "U2")
    device = d.device("J1", "DEMO-CONN-4P-MIXED")
    fn = device.x1
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    objects = {
        "Design": d,
        "UnitDesign": _UNIT_DESIGNS[0],
        "Device": device,
        "Fn": fn,
        "Pin": fn.pins[0],
        "Cable": d.cable("W1", "DEMO-CBL-4G1.5"),
        "TerminalStrip": strip,
        "Run": strip.run("A", 1),
    }
    return [m for label, obj in objects.items() for m in _public_methods(f"live.{label}", obj)]


CASES = [_param(symbol, obj) for symbol, obj in [*_callables(), *_live()]]


@pytest.mark.parametrize("obj", CASES)
def test_signature_and_hints_resolve(obj: object) -> None:
    if not (inspect.isclass(obj) and issubclass(obj, BaseException)):  # no signature, by design
        inspect.signature(obj)  # ty: ignore[invalid-argument-type] -- obj is a callable by construction
    if not inspect.ismethod(obj):  # a live method's `self: "Design"` is quoted on purpose (0111)
        typing.get_type_hints(obj)


def test_terminal_scope_is_not_a_constructor_parameter() -> None:
    assert "_scope" not in inspect.signature(fr.Terminal).parameters
