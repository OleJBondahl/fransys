"""The ast-grep rules in `rules/`: each rule's sites stay at its stock in `sg-counts.toml`.

`ast-grep scan` runs once for the module; a rule marked `forbid` fails on any site, a `count`
rule fails above and below its stock (spec CONSOLIDATE C2; decision root-0356).
"""

import json
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

import pytest
from gate_scan import ROOT

COUNTS = ROOT / "sg-counts.toml"
RULES = ROOT / "rules"


def rule_ids(rules_dir: Path) -> set[str]:
    """The `id:` of every rule file in `rules_dir`."""
    ids = (re.search(r"^id: (\S+)", p.read_text(), re.MULTILINE) for p in rules_dir.glob("*.yml"))
    return {m.group(1) for m in ids if m}


def scan(root: Path) -> dict[str, list[str]]:
    """Run `ast-grep scan` in `root`; the sites `file:line` found by each rule id."""
    binary = Path(sys.executable).parent / "ast-grep"
    done = subprocess.run(  # noqa: S603 -- fixed argv, the venv's own ast-grep
        [str(binary), "scan", "--json=compact"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    # exit 1 means an error-severity rule matched: the sites are in the JSON, not a failure to run
    assert done.returncode in (0, 1), (
        f"ast-grep scan failed in {root}: {done.stderr}; fix rules/ or sgconfig.yml"
    )
    found: dict[str, list[str]] = defaultdict(list)
    for hit in json.loads(done.stdout or "[]"):
        found[hit["ruleId"]].append(f"{hit['file']}:{hit['range']['start']['line'] + 1}")
    return found


def check(counts: dict, ids: set[str], found: dict[str, list[str]]) -> list[str]:
    """One message per rule whose sites disagree with its table, or that has no table or file."""
    problems = [
        f"rules/ has no rule file for sg-counts.toml [{n}]; delete the table"
        for n in sorted(counts.keys() - ids)
    ]
    problems += [
        f"rule {n} has no sg-counts.toml table; add [{n}] with its stock"
        for n in sorted(ids - counts.keys())
    ]
    for name in sorted(counts.keys() & ids):
        table, sites = counts[name], found.get(name, [])
        if len(sites) > table["stock"] or (table["mark"] == "forbid" and sites):
            problems.append(
                f"rule {name} found {len(sites)} sites outside {table['home']}: "
                f"{', '.join(sites)}; move them to {table['home']}"
            )
        elif len(sites) < table["stock"]:
            problems.append(f"lower sg-counts.toml [{name}] to {len(sites)}")
    return problems


@pytest.fixture(scope="module")
def found() -> dict[str, list[str]]:
    return scan(ROOT)


@pytest.mark.private_input  # reads rules/ (R462)
def test_every_rule_stays_at_its_stock(found: dict[str, list[str]]) -> None:
    counts = tomllib.loads(COUNTS.read_text())
    assert not check(counts, rule_ids(RULES), found)


def test_a_site_over_a_forbid_rule_fails() -> None:
    counts = {"r": {"stock": 0, "mark": "forbid", "home": "H"}}
    problems = check(counts, {"r"}, {"r": ["a.py:3"]})
    assert problems == ["rule r found 1 sites outside H: a.py:3; move them to H"]


def test_a_count_rule_fails_above_and_below() -> None:
    counts = {"r": {"stock": 2, "mark": "count", "home": "H"}}
    assert check(counts, {"r"}, {"r": ["a:1", "b:2"]}) == []
    assert "found 3 sites" in check(counts, {"r"}, {"r": ["a:1", "b:2", "c:3"]})[0]
    assert check(counts, {"r"}, {"r": ["a:1"]}) == ["lower sg-counts.toml [r] to 1"]


def test_a_rule_without_a_table_or_a_table_without_a_rule_fails() -> None:
    assert "no sg-counts.toml table" in check({}, {"r"}, {})[0]
    table = {"stock": 0, "mark": "forbid", "home": "H"}
    assert "no rule file" in check({"r": table}, set(), {})[0]
