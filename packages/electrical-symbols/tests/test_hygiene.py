"""Enforce docs/IEC_HANDLING.md on the tracked text: no IEC ids, no forbidden wording, no sourcing.

Each check is a function over (path, text) pairs, so its self-test needs no git.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GUIDE = "docs/SYMBOL_INTERFACE.html"
HANDLING = "docs/IEC_HANDLING.md"
# The lockfile is generated and holds hashes and package-index URLs, not authored text.
SKIPPED = {"uv.lock"}
# The workspace decisions file is private and scanned by test_decisions_hygiene.py.

IEC_ID = re.compile(r"S[0-9]{5}")
# The standard's other item ids: a part reference such as `60617-<digit>...` and a part-item id of
# three two-digit groups. `\b` keeps dates (2026-09-19) and version strings from matching. Nothing
# tracked matches today, not even the guide, so only the guide (never edited) is exempt, as for
# IEC_ID; this file's own pattern text does not match itself.
ITEM_ID = re.compile(r"60617-[0-9]|\b[0-9]{2}-[0-9]{2}-[0-9]{2}\b")
# tests/test_data.py maps the guide's own ids to our slugs, because the guide is never edited and
# still carries them. That dict is the one accepted residual; an id elsewhere in the file counts.
RESIDUAL_FILE = "tests/test_data.py"
RESIDUAL = re.compile(r"^GUIDE_SLUGS = \{.*?^\}\n", re.MULTILINE | re.DOTALL)

# Rule 4 of docs/IEC_HANDLING.md; the words may be split by any whitespace, including a line end.
FORBIDDEN = [
    "iec-compliant",
    "conforms to",
    "certified",
    "official",
    "verified against iec",
    "iec symbols",
]
# The guide (never edited) says "official" and "subscription"; IEC_HANDLING.md and CLAUDE.md state
# the rules and so quote the forbidden phrases; this file holds the lists.
FORBIDDEN_EXEMPT = {GUIDE, HANDLING, "CLAUDE.md", "tests/test_hygiene.py"}

SOURCING = ["confirmed against", "subscription", r"\.pdf", "snapshot", "https?://"]
# CLAUDE.md is not exempt: it describes the rule without using the markers.
SOURCING_EXEMPT = {GUIDE, HANDLING, "tests/test_hygiene.py"}
# The SVG namespace in the generated build/.
ALLOWED_URLS = ("http://www.w3.org/2000/svg",)
# A pin to our own toolkit's release tag is a dependency, not a source citation (D42): exempt in
# pyproject.toml ONLY, and only up to the tag's closing quote -- a branch or another file with the
# same URL still fails.
GRAPHICAL_SYMBOLS_PIN = re.compile(
    r"git\+https://github\.com/OleJBondahl/graphical-symbols@v\d+\.\d+\.\d+(?=\")"
)
GRAPHICAL_SYMBOLS_PIN_EXEMPT_PATH = "pyproject.toml"


def phrases(words):
    """A case-insensitive pattern for the words, with any whitespace between their parts."""
    return re.compile("|".join(w.replace(" ", r"\s+") for w in words), re.IGNORECASE)


def scan(files, pattern, exempt=()):
    """`path:line: match` for every match of the pattern in the files that are not exempt."""
    return [
        f"{path}:{text.count('\n', 0, m.start()) + 1}: {m.group()}"
        for path, text in files
        if path not in exempt
        for m in pattern.finditer(text)
    ]


def id_problems(files):
    """IEC ids everywhere but the guide and the residual dict in tests/test_data.py."""

    def blank(match):  # keeps the line numbers
        return "\n" * match.group().count("\n")

    checked = [
        (path, RESIDUAL.sub(blank, text) if path == RESIDUAL_FILE else text) for path, text in files
    ]
    return scan(checked, IEC_ID, {GUIDE})


def item_id_problems(files):
    """Part references and part-item ids everywhere but the guide."""
    return scan(files, ITEM_ID, {GUIDE})


def phrase_problems(files):
    return scan(files, phrases(FORBIDDEN), FORBIDDEN_EXEMPT)


def sourcing_problems(files):
    def without_urls(path, text):
        for url in ALLOWED_URLS:
            text = text.replace(url, "")
        if path == GRAPHICAL_SYMBOLS_PIN_EXEMPT_PATH:
            text = GRAPHICAL_SYMBOLS_PIN.sub("", text)
        return text

    return scan([(p, without_urls(p, t)) for p, t in files], phrases(SOURCING), SOURCING_EXEMPT)


def tracked_text():
    """(path, text) for every tracked file that reads as UTF-8; other files are skipped."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607  git from PATH
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    files = []
    for name in filter(None, listing.split("\0")):
        if name in SKIPPED:
            continue
        try:
            files.append((name, (ROOT / name).read_text(encoding="utf-8")))
        except OSError, UnicodeDecodeError:
            continue
    return files


FILES = tracked_text()
OLD_ID = "S" + "12345"  # built in two parts so this file holds no id itself
PART_REF = "60617-" + "6"  # likewise for the two item id forms
ITEM = "06-14-" + "02"  # built in two parts so this file holds no item id itself


def test_the_scan_reads_the_tracked_text():
    paths = {path for path, _ in FILES}
    assert {
        "README.md",
        "symbols/fuse.toml",
        "src/electrical_symbols/bundle.json",
    } <= paths
    assert not paths & SKIPPED


def test_no_iec_ids_in_tracked_text():
    assert id_problems(FILES) == []


def test_no_item_ids_in_tracked_text():
    assert item_id_problems(FILES) == []


def test_no_forbidden_phrases_in_tracked_text():
    assert phrase_problems(FILES) == []


def test_no_sourcing_markers_in_tracked_text():
    assert sourcing_problems(FILES) == []


def test_id_check_fires_on_an_old_style_id(tmp_path):
    scratch = tmp_path / "scratch.toml"
    scratch.write_text(f'reference = {{ number = "{OLD_ID}" }}\n', encoding="utf-8")
    files = [("scratch.toml", scratch.read_text(encoding="utf-8"))]
    assert id_problems(files) == [f"scratch.toml:1: {OLD_ID}"]
    assert id_problems([("symbols/fuse.toml", f"a\nb {OLD_ID}0\n")]) == [
        f"symbols/fuse.toml:2: {OLD_ID}"
    ]
    assert id_problems([("symbols/fuse.toml", "number = 'S1234'\nid = 's12345'\n")]) == []


def test_id_check_exempts_only_the_guide_and_the_residual_dict():
    assert id_problems([(GUIDE, f"<code>{OLD_ID}</code>")]) == []
    residual = f'A = 1\nGUIDE_SLUGS = {{\n    "{OLD_ID}": "fuse",\n}}\nB = "{OLD_ID}"\n'
    assert id_problems([(RESIDUAL_FILE, residual)]) == [f"{RESIDUAL_FILE}:5: {OLD_ID}"]
    assert id_problems([("tests/test_gates.py", residual)]) != []


def test_item_id_check_fires_on_a_part_reference_and_on_a_part_item_id():
    assert item_id_problems([("a.md", f"see IEC {PART_REF} {ITEM}\n")]) == [
        f"a.md:1: {PART_REF}",
        f"a.md:1: {ITEM}",
    ]
    assert item_id_problems([("a.md", f"x\n{ITEM}.")]) == [f"a.md:2: {ITEM}"]
    assert item_id_problems([("a.md", f"IEC {PART_REF}0 x")]) == [f"a.md:1: {PART_REF}"]


def test_item_id_check_ignores_dates_versions_and_the_allowed_forms():
    text = "2026-09-19 0.1.0 1.2.3 123-45-67 12-34 IEC-60617-style IEC 60617 60617-x\n"
    assert item_id_problems([("a.md", text)]) == []


def test_item_id_check_exempts_only_the_guide():
    assert item_id_problems([(GUIDE, f"<code>{PART_REF} {ITEM}</code>")]) == []
    assert item_id_problems([(HANDLING, f"{PART_REF}")]) != []


def test_the_residual_is_the_guide_slugs_dict_in_test_data():
    text = dict(FILES)[RESIDUAL_FILE]
    block = RESIDUAL.search(text)
    assert block
    assert len(IEC_ID.findall(block.group())) == len(IEC_ID.findall(text))


@pytest.mark.parametrize("phrase", FORBIDDEN)
def test_phrase_check_fires_on_each_forbidden_phrase(phrase):
    assert phrase_problems([("a.md", f"These are {phrase.upper()}.\n")]) != []
    split = phrase.replace(" ", "\n")
    assert phrase_problems([("a.md", f"x\n{split}")]) == [f"a.md:2: {split}"]


def test_phrase_check_allows_the_rule_4_forms_and_the_exempt_files():
    allowed = (
        "Drawn after the conventions of IEC 60617, based on IEC 60617, IEC-60617-style,\n"
        "not affiliated with or endorsed by IEC; standard = 'IEC 60617'.\n"
    )
    assert phrase_problems([("a.md", allowed)]) == []
    for path in FORBIDDEN_EXEMPT:
        assert phrase_problems([(path, "IEC-compliant")]) == []


@pytest.mark.parametrize(
    "marker",
    ["Confirmed against the list", "a subscription", "list.PDF", "a snapshot", "http://x.org"],
)
def test_sourcing_check_fires_on_each_marker(marker):
    assert sourcing_problems([("a.md", marker)]) != []


def test_sourcing_check_allows_the_svg_namespace_and_the_exempt_files():
    assert (
        sourcing_problems([("build/svg/x.svg", '<svg xmlns="http://www.w3.org/2000/svg">')]) == []
    )
    assert sourcing_problems([("pyproject.toml", "https://github.com/other/repo.git")]) != []
    for path in SOURCING_EXEMPT:
        assert sourcing_problems([(path, "a subscription")]) == []


def test_sourcing_check_allows_the_graphical_symbols_tag_pin_in_pyproject_toml_only():
    pinned = 'dependencies = ["graphical-symbols @ git+https://github.com/OleJBondahl/graphical-symbols@v0.1.2"]\n'
    assert sourcing_problems([("pyproject.toml", pinned)]) == []


def test_sourcing_check_still_fires_on_the_graphical_symbols_url_at_a_branch():
    # D42's exemption is anchored on an exact tag: a branch is still a sourcing marker (it is not
    # even a valid direct-reference pin -- decision 0014/0017's gate would reject it too).
    branch = 'x = "git+https://github.com/OleJBondahl/graphical-symbols@main"\n'
    assert sourcing_problems([("pyproject.toml", branch)]) != []


def test_sourcing_check_still_fires_on_the_graphical_symbols_tag_outside_pyproject_toml():
    # The same URL is a real citation anywhere but the one file that names it as a dependency.
    # Properly quoted (a real closing `"` for GRAPHICAL_SYMBOLS_PIN's lookahead to find): an
    # unquoted string here would never match the pattern regardless of path, so the path guard
    # itself would go untested.
    tagged = '"git+https://github.com/OleJBondahl/graphical-symbols@v0.1.2"\n'
    assert sourcing_problems([("README.md", tagged)]) != []


STEMS = sorted(p.stem for p in (ROOT / "symbols").glob("*.toml"))


def table_slugs(text):
    """The slugs in the first column of the symbol table of a Markdown file, sorted."""
    return sorted(re.findall(r"^\| `([^`]+)` \|", text, re.MULTILINE))


@pytest.mark.parametrize("path", ["README.md"])
def test_every_symbol_is_in_the_symbol_table(path):
    assert table_slugs(dict(FILES)[path]) == STEMS


def test_table_check_fails_on_a_missing_or_extra_slug():
    table = "| Slug | Name |\n|---|---|\n" + "".join(f"| `{s}` | x |\n" for s in STEMS)
    assert table_slugs(table) == STEMS
    assert table_slugs(table.replace(f"| `{STEMS[0]}` | x |\n", "")) != STEMS
    assert table_slugs(table + "| `no-such-symbol` | x |\n") != STEMS
