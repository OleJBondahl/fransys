"""Tier words (API-CLARITY C1, A1): each `fr.*` function and handle method opens with one.

The namespaces `d.*`, `d.detail.*`, `d.layout.*` and `fr.derive.*` set their tier and carry none.
"""

import inspect
import re

import fransys as fr

WORDS = ("Core", "Detail", "Read", "Output")
OUTPUT = tuple(
    f"fr.{n}"
    for n in [
        "build",
        "check",
        "report",
        "write",
        "document",
        "release",
        "releases",
        "diff",
        "verify",
        "rebaseline",
    ]
)
TIERS = {
    "fr.design": "Core",
    "fr.unit": "Core",
    "fr.settings": "Core",
    "fr.parts": "Detail",
    "fr.parts_module": "Detail",
    "fr.lint": "Read",
    "fr.readability": "Read",
    "fr.export_names": "Read",
    **dict.fromkeys(OUTPUT, "Output"),
    "Fn.plc": "Core",
    "Fn.scale": "Core",
    "Fn.pole": "Core",
    "Fn.limits": "Core",
    "Terminal.limits": "Core",
    "TerminalStrip.run": "Core",
    "Cable.spare": "Core",
    "Cable.core": "Detail",
}
_WORD = re.compile(rf"^({'|'.join(WORDS)}): ")


def _functions(cls: type) -> dict[str, object]:
    return {n: f for n, f in inspect.getmembers(cls, inspect.isfunction) if not n.startswith("_")}


def _cable_class() -> type:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    return type(d.cable("W1", "DEMO-CBL-4G1.5"))


def tiered() -> dict[str, object]:
    """Every callable that must carry a tier word, by its spelling."""
    found: dict[str, object] = {
        f"fr.{n}": getattr(fr, n) for n in fr.__all__ if inspect.isfunction(getattr(fr, n))
    }
    handles = {
        "Fn": fr.Fn,
        "Device": fr.Device,
        "Terminal": fr.Terminal,
        "TerminalStrip": fr.TerminalStrip,
        "Run": fr.Run,
        "Cable": _cable_class(),
    }
    for label, cls in handles.items():
        for name, func in _functions(cls).items():
            found.setdefault(f"{'TerminalStrip' if label == 'Run' else label}.{name}", func)
    return found


def namespaced() -> dict[str, object]:
    """Every callable a namespace tiers: it carries no word."""
    found = {f"d.{n}": f for n, f in _functions(fr.Design).items()}
    found |= {f"d.detail.{n}": f for n, f in _functions(fr.Detail).items()}
    found |= {f"d.layout.{n}": f for n, f in _functions(fr.Layout).items()}
    found |= {f"fr.derive.{n}": getattr(fr.derive, n) for n in fr.derive.__all__}
    return {k: v for k, v in found.items() if callable(v)}


def word_of(call: object) -> str | None:
    match = _WORD.match(inspect.getdoc(call) or "")
    return match.group(1) if match else None


def test_every_function_and_handle_method_has_its_tier_word():
    wrong = {k: word_of(v) for k, v in tiered().items() if word_of(v) != TIERS.get(k)}
    assert not wrong, f"tier word missing or not the ruled one: {wrong}"
    assert set(tiered()) == set(TIERS), set(tiered()) ^ set(TIERS)


def test_a_docstring_holds_one_tier_word():
    twice = [
        k
        for k, v in tiered().items()
        if len(re.findall(rf"\b({'|'.join(WORDS)}): ", inspect.getdoc(v) or "")) > 1
    ]
    assert not twice, f"more than one tier word: {twice}"


def test_a_namespaced_call_carries_no_tier_word():
    wrong = sorted(k for k, v in namespaced().items() if word_of(v))
    assert not wrong, f"namespaced calls with a tier word: {wrong}"


def test_the_collectors_see_calls():
    assert {"fr.build", "Fn.plc", "Cable.core"} <= set(tiered())
    assert {"d.device", "d.detail.wire", "d.layout.chain"} <= set(namespaced())
    assert any(k.startswith("fr.derive.") for k in namespaced())
