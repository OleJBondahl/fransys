"""Every fix text is an action a consumer can take (designer R382.3, decision el-0051).

An ERROR or WARNING fix names a public `fr.<name>` call, an author call `d.<name>(...)`, a
settings or part-file key (`[section] key`, `key = value`), or says `No call clears this:`,
the one known-limit marker. It never names an internal type, a private module or a library hook.
"""

import re

import fransys as fr
import pytest
from test_finding_fix_grammar import GROUPS, NO_CALL

from fransys_model.kernel import CodeInfo, Severity

FR_NAME = re.compile(r"\bfr\.([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))?")
# an internal name: a package module, a CamelCase type with an attribute, a `kit` or a `Skipped`
INTERNAL = re.compile(r"\bfransys_\w+|\b[A-Z][a-z]+(?:[A-Z][a-z]*)*\.[a-z_]\w*|\bkit\b|\bSkipped\b")
ACTION = re.compile(r"\b\w+(?:\.\w+)*\(|\[\w[\w .-]*\]|[\w>] = |\.toml\b")
COUNTED = [
    pytest.param(info, id=info.code)
    for infos in GROUPS.values()
    for info in infos
    if set(info.severities) & {Severity.ERROR, Severity.WARNING}
]


def _problem(fix: str) -> str | None:
    for root, leaf in FR_NAME.findall(fix):
        if root == "derive" and leaf in fr.derive.__all__:
            continue
        if root not in {*fr.__all__, "colours"}:  # `fr.colours` is the public colour module
            return f"`fr.{root}` is not in fransys.__all__"
    if internal := INTERNAL.search(fix):
        return f"internal name {internal.group(0)!r}"
    if not fix.startswith(NO_CALL) and not ACTION.search(fix.partition("Write:")[2]):
        return "no call, key or known-limit marker"
    return None


@pytest.mark.parametrize("info", COUNTED)
def test_a_fix_is_an_action_a_consumer_can_take(info: CodeInfo) -> None:
    assert _problem(info.fix) is None, info.fix


@pytest.mark.parametrize(
    "fix",
    [
        "Name the port in the Pick.ports of the symbol. Write: Pick(ports={})",
        "Call fr.nothing_public(<x>). Write: fr.nothing_public(<x>)",
        "Pass the Skipped that fransys_el.build gave. Write: nothing",
        "Do something about it.",
    ],
)
def test_the_check_refuses_an_internal_or_empty_fix(fix: str) -> None:
    assert _problem(fix) is not None


def test_the_check_takes_the_known_limit_and_a_call() -> None:
    assert _problem("No call clears this: send the smallest model that shows it.") is None
    assert _problem("Name it. Write: fr.build(settings=fr.settings(path))") is None
