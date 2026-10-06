"""Every public callable's signature and annotations resolve at runtime (no NameError).

An annotation that names a type imported only under TYPE_CHECKING breaks `inspect.signature`
consumers, `just api` and the guide examples; this checks each surface name and each public
method of each public class.
"""

import importlib
import inspect
import typing

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


CASES = [_param(symbol, obj) for symbol, obj in _callables()]


@pytest.mark.parametrize("obj", CASES)
def test_signature_and_hints_resolve(obj: object) -> None:
    if not (inspect.isclass(obj) and issubclass(obj, BaseException)):  # no signature, by design
        inspect.signature(obj)  # ty: ignore[invalid-argument-type] -- obj is a callable by construction
    typing.get_type_hints(obj)
