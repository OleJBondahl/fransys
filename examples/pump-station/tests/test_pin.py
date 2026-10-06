"""The one Fransys dependency is pinned at a release tag (CLAUDE.md rule 2), or on a work branch at
one main sha with every workspace package overridden to it (rule 3); uv.lock holds every Fransys
package at one and the same commit.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "uv.lock"
SOURCE = re.compile(r"fransys(?:-dev)?\?subdirectory=[^#\"]*?(?:&rev=[^#\"]*)?#([0-9a-f]{40})")
TAG_PIN = re.compile(
    r"^fransys @ git\+https://github\.com/OleJBondahl/fransys@v\d+\.\d+\.\d+"
    r"#subdirectory=packages/fransys$"
)
SHA_PIN = re.compile(
    r"^fransys @ git\+https://github\.com/OleJBondahl/fransys-dev@[0-9a-f]{40}"
    r"#subdirectory=packages/fransys$"
)


def locked_shas(lock_text: str) -> dict[str, str]:
    shas: dict[str, str] = {}
    for package in tomllib.loads(lock_text)["package"]:
        git = package.get("source", {}).get("git", "")
        match = SOURCE.search(git)
        if match:
            shas[package["name"]] = match.group(1)
    return shas


def pin_problems(pyproject_text: str) -> list[str]:
    """What is wrong with the pin: not one `fransys` line, a tag pin with an override, or a sha pin without one."""
    data = tomllib.loads(pyproject_text)
    lines = [d for d in data["project"]["dependencies"] if d.startswith("fransys")]
    if len(lines) != 1:
        return [f"expected one fransys dependency, got {lines}"]
    has_override = "override-dependencies" in data.get("tool", {}).get("uv", {})
    if SHA_PIN.match(lines[0]):
        return [] if has_override else ["a sha pin needs override-dependencies"]
    if not TAG_PIN.match(lines[0]):
        return [f"not a release-tag pin: {lines[0]}"]
    return ["override-dependencies is a sha-pin leftover"] if has_override else []


def test_fransys_is_pinned_at_a_tag_or_one_branch_sha() -> None:
    assert pin_problems((ROOT / "pyproject.toml").read_text()) == []


def test_the_pin_check_fails_on_a_floating_pin() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert pin_problems(re.sub(r"@v\d+\.\d+\.\d+#", "@main#", text, count=1))
    assert pin_problems(text.replace("[tool.uv]\n", "[tool.uv]\noverride-dependencies = []\n"))


def test_the_pin_check_accepts_a_branch_sha_with_its_override() -> None:
    sha = "0" * 40
    line = f"fransys @ git+https://github.com/OleJBondahl/fransys-dev@{sha}#subdirectory=packages/fransys"
    base = f'[project]\ndependencies = ["{line}"]\n[tool.uv]\n'
    assert pin_problems(base + "override-dependencies = []\n") == []
    assert pin_problems(base)


def test_every_fransys_package_is_at_one_sha() -> None:
    shas = locked_shas(LOCK.read_text())
    assert len(shas) >= 12, shas
    assert len(set(shas.values())) == 1, shas


def test_the_check_sees_a_second_sha() -> None:
    text = LOCK.read_text()
    sha = next(iter(locked_shas(text).values()))
    broken = text.replace("#" + sha, "#" + "0" * 40, 1)
    assert len(set(locked_shas(broken).values())) == 2
