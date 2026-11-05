"""Field case: a consumer `[font]` is told it reaches only the new engine's drawings.
The bug: the build took the keys with no sign that the schematic engine still drew with the built-in font.
Fixed by layout-0323 (SETTINGS-A2b, Ruling 15), one WARNING per key naming it, its value and its effect; MODEL-TEXT removes it."""

from pathlib import Path

import fransys as fr

FONTS = Path(__file__).parents[2] / "packages/fransys/tests/fixtures/fonts"
FILES = f'files = ["{FONTS / "DejaVuSans.ttf"}", "{FONTS / "DejaVuSans-Bold.ttf"}"]\n'
CODE = "SETTING_NEW_ENGINE_ONLY"


def _warnings(tmp_path: Path, text: str) -> list[str]:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    result = fr.build(d, settings=fr.settings(path))
    return [f.message for f in result.findings if f.code == CODE]


def test_one_warning_per_key_the_consumer_set(tmp_path: Path) -> None:
    got = _warnings(tmp_path, f"[font]\nname = 'Vera'\n{FILES}")
    assert len(got) == 2
    for key in ("font name = 'Vera'", "font files = "):
        assert len([m for m in got if key in m]) == 1
    assert all("new engine" in m and "old engine" in m for m in got)


def test_a_build_with_no_such_key_gives_none(tmp_path: Path) -> None:
    assert _warnings(tmp_path, "") == []


def test_the_warning_never_blocks_the_write(tmp_path: Path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text(f"[font]\n{FILES}", encoding="utf-8")
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    result = fr.build(d, settings=fr.settings(path))
    assert [f.severity.name for f in result.findings if f.code == CODE] == ["WARNING"]
    assert not [f for f in result.findings if f.severity.name == "ERROR"]
