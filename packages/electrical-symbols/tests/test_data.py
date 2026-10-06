"""Data-only gates for symbols/*.toml: stdlib tomllib, no toolkit code; the guide is read from the
toolkit's distribution.
"""

import copy
import html
import importlib.resources
import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).parent.parent
# The toolkit ships its design guide as package data (root decision 0015, toolkit decision D38):
# reading it through importlib.resources works whether graphical_symbols is installed from its
# pinned git tag (the normal case) or from a local editable override, and it is never a sibling
# checkout path -- there is no "../graphical-symbols" any more, the toolkit is its own repository.
# `files()` is typed to return the abstract `Traversable`, but graphical_symbols is a regular,
# non-namespace, non-zipped package, so this is always a real `Path` at runtime.
GUIDE = cast(
    "Path", importlib.resources.files("graphical_symbols").joinpath("docs/SYMBOL_INTERFACE.html")
)
SYMBOL_FILES = sorted((ROOT / "symbols").glob("*.toml"))
PORT_ID = re.compile(r"^[a-z][a-z0-9_]*$")
# Numbers that are not lengths in modules: the schema version, arc angles, counts and pitches.
NOT_LENGTHS = {"schema", "repeat", "pole_pitch"}
ARC_ANGLES = {"start", "end"}
# The guide is never edited, so its five examples carry its own ids (six in all: the push-button
# block also names the actuator); each is compared with the repo file after the id is replaced by
# the slug in `number` and in `use` (see D38).
GUIDE_SLUGS = {
    "S00016": "connection-point",
    "S00171": "actuator-push",
    "S00227": "make-contact",
    "S00230": "change-over-contact",
    "S00254": "push-button",
    "S00305": "operating-device",
}
# The one line a file may add to its guide example (see D3 and C1 in the decisions file).
GUIDE_EXTRA_LINE = {"push-button": "pole_pitch = 8\n"}
# Guide examples the file draws mirrored top to bottom, by owner ruling (D44): the file is checked
# against the guide's block mirrored (`check_mirrored`), not compared verbatim.
GUIDE_MIRRORED = {"change-over-contact"}
# Each protective-earth variant copies its base's geometry (see D33 and D34 in the decisions file).
VARIANT_PAIRS = [
    ("motor-3ph", "motor-3ph-pe"),
    ("motor-1ph", "motor-1ph-pe"),
    ("rectifier", "rectifier-pe"),
]
PE_NODE = {"ports": ["pe"], "potential": "protective_earth"}
# Top-level keys a variant may differ in; every other key must equal the base's.
VARIANT_OWN_KEYS = {
    "name",
    "reference",
    "lint_allow",
    "ports",
    "paths",
    "elements",
    "slots",
    "nodes",
}


def load_toml(path):
    with path.open("rb") as file:
        return tomllib.load(file)


LIBRARY = load_toml(ROOT / "library.toml")


def check_stem(doc, stem):
    number = doc["reference"]["number"]
    return [] if number == stem else [f"number {number} differs from file stem {stem}"]


def check_number_pattern(doc):
    number = doc["reference"]["number"]
    if re.match(LIBRARY["number_pattern"], number):
        return []
    return [f"number {number} does not match {LIBRARY['number_pattern']}"]


def check_standard(doc):
    standard = doc["reference"]["standard"]
    if standard == LIBRARY["standard"]:
        return []
    return [f"standard {standard!r} differs from library.toml {LIBRARY['standard']!r}"]


def check_status(doc):
    return [] if doc["status"] == "unverified" else [f"status is {doc['status']!r}"]


def check_name(doc):
    return [] if doc["name"].strip() else ["name is empty"]


def port_ids(doc):
    ports = doc.get("ports", [])
    if isinstance(ports, dict):
        return list(ports)
    return [port["id"] for port in ports]


def check_port_ids(doc):
    return [f"port id {i!r} is not a role id" for i in port_ids(doc) if not PORT_ID.match(i)]


def numbers(node, path=""):
    """Yield (path, value) for every module-unit number in a parsed TOML value."""
    if isinstance(node, bool):
        return
    if isinstance(node, int | float):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in NOT_LENGTHS or (key in ARC_ANGLES and "arc" in node):
                continue
            yield from numbers(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from numbers(value, f"{path}[{index}]")


def check_drawing_grid(doc):
    return [
        f"{path} = {value} is not a multiple of 0.125"
        for path, value in numbers(doc)
        if not (value * 8).is_integer()
    ]


def duplicate_numbers(docs):
    seen = [doc["reference"]["number"] for doc in docs]
    return sorted({n for n in seen if seen.count(n) > 1})


def guide_blocks():
    """Map slug to the guide's TOML example blocks: HTML-unescaped, the guide's ids replaced."""
    page = GUIDE.read_bytes().decode("utf-8")
    blocks = {}
    for raw in re.findall(r'<pre data-lang="toml"><code>(.*?)</code></pre>', page, re.DOTALL):
        block = re.sub(
            r'\b(number|use) = "([^"]+)"',
            lambda m: f'{m[1]} = "{GUIDE_SLUGS[m[2]]}"',
            html.unescape(raw),
        )
        blocks[re.findall(r'number = "([^"]+)"', block)[0]] = block
    return blocks


def check_verbatim(number, text, block):
    lines = text.splitlines(keepends=True)
    extra = GUIDE_EXTRA_LINE.get(number)
    if extra:
        if lines.count(extra) != 1:
            return [f"{number} lacks exactly one line {extra!r}"]
        lines.remove(extra)
    return [] if "".join(lines) == block else [f"{number} differs from the guide's block"]


def mirror(node):
    """A parsed symbol mirrored top to bottom: every `at` and `line` point loses its y sign,
    every N/S `dir` swaps, and a through path swaps its ends (the lint wants it to run top to
    bottom). Nothing else moves (slot sides, boxes, ids and the other paths are unchanged).
    """
    if isinstance(node, list):
        return [mirror(value) for value in node]
    if not isinstance(node, dict):
        return node
    if node.get("through") is True:
        node = {**node, "from": node["to"], "to": node["from"]}
    flipped = {}
    for key, value in node.items():
        if key == "at":
            flipped[key] = [value[0], -value[1]]
        elif key == "line":
            flipped[key] = [[x, -y] for x, y in value]
        elif key == "dir":
            flipped[key] = {"N": "S", "S": "N"}.get(value, value)
        else:
            flipped[key] = mirror(value)
    return flipped


def check_mirrored(doc, block_doc):
    return [] if doc == mirror(block_doc) else ["differs from the guide's block mirrored"]


def entries(doc, key):
    """A list value as is, a table as (key, value) pairs, so both compare entry by entry."""
    value = doc.get(key, [])
    return list(value.items()) if isinstance(value, dict) else value


def added(base, variant, key):
    """The entries of `key` that the variant has and the base lacks."""
    return [entry for entry in entries(variant, key) if entry not in entries(base, key)]


def check_variant(base, variant):
    """The variant is its base plus a pe port, its lead, a protective-earth node and marking.pe."""
    lost = [
        (key, e)
        for key in ("ports", "paths", "elements", "slots", "nodes")
        for e in added(variant, base, key)
    ]
    others = sorted(
        key
        for key in set(base) | set(variant)
        if key not in VARIANT_OWN_KEYS and base.get(key) != variant.get(key)
    )
    ports, elements = added(base, variant, "ports"), added(base, variant, "elements")
    lead = elements[0].get("polyline", []) if len(elements) == 1 else []
    expected = {
        f"top-level keys differ from the base: {others}": not others,
        "number is not the base's number plus -pe": (
            variant["reference"]["number"] == base["reference"]["number"] + "-pe"
        ),
        f"base entries are missing or changed: {lost}": not lost,
        f"extra ports {ports} are not one port `pe` facing N": (
            [p["id"] for p in ports] == ["pe"] and ports[0]["dir"] == "N"
        ),
        f"extra elements {elements} are not one polyline lead at pe": (
            bool(ports) and bool(lead) and ports[0]["at"] in (lead[0], lead[-1])
        ),
        "the variant adds a path: pe has none": not added(base, variant, "paths"),
        "the only extra node is not pe with protective_earth": (
            added(base, variant, "nodes") == [PE_NODE]
        ),
        "the only extra slot is not marking.pe": (
            [name for name, _ in added(base, variant, "slots")] == ["marking.pe"]
        ),
    }
    return [problem for problem, ok in expected.items() if not ok]


CHECKS = {
    "number-pattern": check_number_pattern,
    "standard": check_standard,
    "status": check_status,
    "name": check_name,
    "port-ids": check_port_ids,
    "drawing-grid": check_drawing_grid,
}
CASES = [(path, check) for path in SYMBOL_FILES for check in CHECKS]
GUIDE_BLOCKS = guide_blocks()

GOOD = {
    "schema": 1,
    "name": "Make contact, general symbol",
    "status": "unverified",
    "reference": {"standard": "IEC 60617", "number": "make-contact"},
    "ports": [{"id": "in", "at": [0, -2], "dir": "N"}],
    "elements": [
        {"line": [[0, 1], [-1, -1]]},
        {"arc": [0, 0], "r": 0.5, "start": 33.3, "end": 100.7},
    ],
    "parts": [{"as": "main", "use": "make-contact", "repeat": 3}],
    "pole_pitch": 8,
}
BROKEN = {
    "schema": 1,
    "name": "",
    "status": "verified",
    "reference": {"standard": "ISO 14617", "number": "X1"},
    "ports": [{"id": "A1", "at": [0.1, -2], "dir": "N"}],
}


def test_library_toml_has_the_three_keys():
    assert LIBRARY == {
        "standard": "IEC 60617",
        "title": "Electrical graphical symbols",
        "number_pattern": r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    }


@pytest.mark.parametrize(("path", "check"), CASES, ids=[f"{p.stem}-{c}" for p, c in CASES])
def test_symbol_file(path, check):
    assert CHECKS[check](load_toml(path)) == []


@pytest.mark.parametrize("path", SYMBOL_FILES, ids=[p.stem for p in SYMBOL_FILES])
def test_number_equals_file_stem(path):
    assert check_stem(load_toml(path), path.stem) == []


def test_numbers_are_unique():
    assert duplicate_numbers([load_toml(path) for path in SYMBOL_FILES]) == []


@pytest.mark.parametrize("check", CHECKS)
def test_check_passes_a_good_doc(check):
    assert CHECKS[check](GOOD) == []


@pytest.mark.parametrize("check", CHECKS)
def test_check_flags_a_broken_doc(check):
    assert CHECKS[check](BROKEN) != []


def test_stem_check_passes_a_good_doc_and_flags_a_broken_one():
    assert check_stem(GOOD, "make-contact") == []
    assert check_stem(GOOD, "fuse") != []


def test_duplicate_numbers_are_flagged():
    assert duplicate_numbers([GOOD, GOOD, BROKEN]) == ["make-contact"]


def test_grid_check_ignores_off_grid_arc_angles():
    arc = {"arc": [0, 0], "r": 0.5, "start": 33.3, "end": 100.7}
    assert check_drawing_grid({"elements": [arc]}) == []


def test_grid_check_flags_start_and_end_outside_an_arc():
    for key in ("start", "end"):
        assert check_drawing_grid({"elements": [{"line": [[0, 0], [1, 1]], key: 0.1}]}) != []


def test_grid_check_ignores_off_grid_schema_repeat_and_pole_pitch():
    doc = {"schema": 0.1, "pole_pitch": 0.1, "parts": [{"as": "main", "repeat": 0.1}]}
    assert check_drawing_grid(doc) == []


def test_port_id_check_covers_composite_rename_maps():
    assert check_port_ids({"ports": {"in": "contact.in"}}) == []
    assert check_port_ids({"ports": {"A1": "contact.in"}}) != []


def guide_is_the_toolkits_own_copy(resolved: Path) -> bool:
    """False when `resolved` sits inside this workspace's own tracked source tree.

    A resource resolved from the pinned distribution lands under the environment's installed
    packages (`.venv/...`), never under `packages/`; a stray sibling checkout or a local path
    override left in `[tool.uv.sources]` would resolve under `packages/` instead, silently
    satisfying this gate against our own tree again instead of the toolkit's real distribution.
    """
    workspace_packages = ROOT.parent
    return workspace_packages not in resolved.parents and resolved != workspace_packages


def test_guide_is_read_from_the_toolkits_distribution_not_a_workspace_path():
    assert guide_is_the_toolkits_own_copy(GUIDE.resolve())


def test_the_distribution_path_check_can_fail():
    workspace_path = ROOT.parent / "graphical-symbols" / "docs" / "SYMBOL_INTERFACE.html"
    assert not guide_is_the_toolkits_own_copy(workspace_path)


def test_guide_has_the_five_example_blocks():
    assert sorted(GUIDE_BLOCKS) == [
        "change-over-contact",
        "connection-point",
        "make-contact",
        "operating-device",
        "push-button",
    ]


def test_change_over_contact_has_com_facing_north_and_no_and_nc_facing_south():
    doc = load_toml(ROOT / "symbols" / "change-over-contact.toml")
    dirs = {port["id"]: port["dir"] for port in doc["ports"]}
    assert dirs == {"com": "N", "no": "S", "nc": "S"}


@pytest.mark.parametrize("number", sorted(set(GUIDE_BLOCKS) - GUIDE_MIRRORED))
def test_guide_examples_verbatim(number):
    text = (ROOT / "symbols" / f"{number}.toml").read_bytes().decode("utf-8")
    assert check_verbatim(number, text, GUIDE_BLOCKS[number]) == []


@pytest.mark.parametrize("number", sorted(GUIDE_MIRRORED))
def test_mirrored_guide_examples_are_the_guide_block_turned_top_to_bottom(number):
    doc = load_toml(ROOT / "symbols" / f"{number}.toml")
    assert check_mirrored(doc, tomllib.loads(GUIDE_BLOCKS[number])) == []


def test_mirrored_check_flags_the_unmirrored_block_and_any_drift():
    block = tomllib.loads(GUIDE_BLOCKS["change-over-contact"])
    good = mirror(block)
    assert mirror(good) == block
    assert check_mirrored(good, block) == []
    assert check_mirrored(block, block) != []
    moved = copy.deepcopy(good)
    moved["elements"][4]["line"][1][1] += 0.25
    assert check_mirrored(moved, block) != []
    unturned = copy.deepcopy(good)
    unturned["ports"][0]["dir"] = block["ports"][0]["dir"]
    assert check_mirrored(unturned, block) != []
    same_path = copy.deepcopy(good)
    same_path["paths"][0]["from"] = block["paths"][0]["from"]
    same_path["paths"][0]["to"] = block["paths"][0]["to"]
    assert check_mirrored(same_path, block) != []
    slot = copy.deepcopy(good)
    slot["slots"]["tag"]["side"] = "E"
    assert check_mirrored(slot, block) != []


def test_verbatim_check_flags_altered_blocks():
    block = GUIDE_BLOCKS["make-contact"]
    assert check_verbatim("make-contact", block, block) == []
    assert check_verbatim("make-contact", block.replace("-1, -1", "-1, -1.5"), block) != []
    assert check_verbatim("make-contact", block.replace("\n", "\r\n"), block) != []
    assert check_verbatim("make-contact", "pole_pitch = 8\n" + block, block) != []
    push_button = GUIDE_BLOCKS["push-button"]
    with_pitch = push_button.replace("\n\n", "\npole_pitch = 8\n\n", 1)
    assert check_verbatim("push-button", with_pitch, push_button) == []
    assert check_verbatim("push-button", push_button, push_button) != []
    assert check_verbatim("push-button", with_pitch.replace("8", "12"), push_button) != []


def test_guide_ids_are_replaced_by_slugs_only_in_number_and_use():
    for slug, block in GUIDE_BLOCKS.items():
        assert not any(guide_id in block for guide_id in GUIDE_SLUGS)
        assert f'number = "{slug}"' in block
    push_button = GUIDE_BLOCKS["push-button"]
    assert 'use = "make-contact"' in push_button
    assert 'use = "actuator-push"' in push_button
    text = push_button.replace('number = "push-button"', 'number = "fuse"')
    assert check_verbatim("push-button", text, push_button) != []


def test_number_pattern_accepts_slugs_and_rejects_malformed_ones():
    for number in ("fuse", "motor-3ph", "motor-3ph-pe", "converter-dc-dc", "a1"):
        assert check_number_pattern({"reference": {"number": number}}) == []
    for number in ("Fuse", "motor-3ph-PE", "3ph", "motor-", "-motor", "motor--3ph", "motor_3ph"):
        assert check_number_pattern({"reference": {"number": number}}) != []
    for number in ("motor.3ph", "motor 3ph", ""):
        assert check_number_pattern({"reference": {"number": number}}) != []


def test_variant_pairs_cover_every_pe_file():
    assert sorted(v for _, v in VARIANT_PAIRS) == [
        p.stem for p in SYMBOL_FILES if p.stem.endswith("-pe")
    ]


@pytest.mark.parametrize(("base", "variant"), VARIANT_PAIRS, ids=[v for _, v in VARIANT_PAIRS])
def test_variant_is_its_base_plus_the_pe_lead(base, variant):
    files = ROOT / "symbols"
    assert (
        check_variant(load_toml(files / f"{base}.toml"), load_toml(files / f"{variant}.toml")) == []
    )


def test_variant_check_flags_drift_and_extras():
    base = load_toml(ROOT / "symbols" / "motor-1ph.toml")
    good = load_toml(ROOT / "symbols" / "motor-1ph-pe.toml")
    assert check_variant(base, good) == []

    def flagged(edit):
        variant = copy.deepcopy(good)
        edit(variant)
        return check_variant(base, variant) != []

    assert flagged(lambda v: v["elements"][2].update(r=2.5))
    assert flagged(lambda v: v["elements"].pop(0))
    assert flagged(lambda v: v["elements"].append({"line": [[0, 0], [1, 1]]}))
    assert flagged(lambda v: v["elements"].pop())
    assert flagged(lambda v: v["ports"][0].update(at=[-2, -5]))
    assert flagged(lambda v: v["ports"].append({"id": "extra", "at": [5, -5], "dir": "N"}))
    assert flagged(lambda v: v["ports"][-1].update(dir="E"))
    assert flagged(lambda v: v["paths"].append({"from": "u", "to": "pe", "kind": "conductor"}))
    assert flagged(lambda v: v["nodes"][0].update(potential="earth"))
    assert flagged(lambda v: v["slots"]["tag"].update(at=[-4, 0]))
    assert flagged(lambda v: v["slots"].pop("marking.pe"))
    assert flagged(lambda v: v["slots"].update(value={"at": [0, 4], "side": "S", "box": [2, 1]}))
    assert flagged(lambda v: v["reference"].update(number="motor-1ph-xx"))
    assert flagged(lambda v: v.update(status="verified"))


def test_variant_check_flags_a_base_that_gained_a_key_or_a_node():
    base = load_toml(ROOT / "symbols" / "motor-1ph.toml")
    good = load_toml(ROOT / "symbols" / "motor-1ph-pe.toml")
    with_pitch = copy.deepcopy(base) | {"pole_pitch": 8}
    assert any("pole_pitch" in problem for problem in check_variant(with_pitch, good))
    with_node = copy.deepcopy(base) | {"nodes": [{"ports": ["u"], "potential": "frame"}]}
    assert any("nodes" in problem for problem in check_variant(with_node, good))
