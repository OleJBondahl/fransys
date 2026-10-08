"""The one Fransys dependency is pinned at a release tag (CLAUDE.md rule 2); uv.lock holds every
Fransys package at one and the same commit.
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


def locked_shas(lock_text: str) -> dict[str, str]:
    shas: dict[str, str] = {}
    for package in tomllib.loads(lock_text)["package"]:
        git = package.get("source", {}).get("git", "")
        match = SOURCE.search(git)
        if match:
            shas[package["name"]] = match.group(1)
    return shas


def pin_problems(pyproject_text: str) -> list[str]:
    """What is wrong with the pin: not one `fransys` line, not a release tag, or an override left over."""
    data = tomllib.loads(pyproject_text)
    lines = [d for d in data["project"]["dependencies"] if d.startswith("fransys")]
    if len(lines) != 1:
        return [f"expected one fransys dependency, got {lines}"]
    has_override = "override-dependencies" in data.get("tool", {}).get("uv", {})
    if not TAG_PIN.match(lines[0]):
        return [f"not a release-tag pin: {lines[0]}"]
    return ["override-dependencies is a sha-pin leftover"] if has_override else []


def test_fransys_is_pinned_at_a_tag() -> None:
    assert pin_problems((ROOT / "pyproject.toml").read_text()) == []


def test_the_pin_check_fails_on_a_floating_pin() -> None:
    tag = (
        "fransys @ git+https://github.com/OleJBondahl/fransys@v0.13.4#subdirectory=packages/fransys"
    )
    text = f'[project]\ndependencies = ["{tag}"]\n[tool.uv]\n'
    assert pin_problems(text) == []
    assert pin_problems(re.sub(r"@v\d+\.\d+\.\d+#", "@main#", text, count=1))
    assert pin_problems(text.replace("[tool.uv]\n", "[tool.uv]\noverride-dependencies = []\n"))


def test_every_fransys_package_is_at_one_sha() -> None:
    shas = locked_shas(LOCK.read_text())
    assert len(shas) >= 12, shas
    assert len(set(shas.values())) == 1, shas


def test_the_check_sees_a_second_sha() -> None:
    text = LOCK.read_text()
    sha = next(iter(locked_shas(text).values()))
    broken = text.replace("#" + sha, "#" + "0" * 40, 1)
    assert len(set(locked_shas(broken).values())) == 2
