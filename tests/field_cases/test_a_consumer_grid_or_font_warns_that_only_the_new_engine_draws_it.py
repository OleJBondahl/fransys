"""Field case: a consumer `[grid]` or `[font]` is told it reaches only the new engine's drawings.

The engineering shape: a small cabinet design built with a settings file that names a
`module_mm` and a measured font (two TrueType files).

The bug: the build took the keys and gave no sign that today's schematic engine still draws with
the built-in grid and font, so the drawings looked ignored. Each key gets one WARNING that names
it, its value and the effect; layout-0323 (SETTINGS-A2b, Ruling 15) added it, and MODEL-TEXT
removes it.
"""

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
    got = _warnings(tmp_path, f"[grid]\nmodule_mm = 2.0\n[font]\nname = 'Vera'\n{FILES}")
    assert len(got) == 3
    for key in ("grid module_mm = 2.0", "font name = 'Vera'", "font files = "):
        assert len([m for m in got if key in m]) == 1
    assert all("new engine" in m and "old engine" in m for m in got)


def test_a_build_with_no_such_key_gives_none(tmp_path: Path) -> None:
    assert _warnings(tmp_path, "") == []
    assert _warnings(tmp_path, "[grid]\nmodule_mm = 2.5\n") == []


def test_the_warning_never_blocks_the_write(tmp_path: Path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text("[grid]\nmodule_mm = 2.0\n", encoding="utf-8")
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    result = fr.build(d, settings=fr.settings(path))
    assert [f.severity.name for f in result.findings if f.code == CODE] == ["WARNING"]
    assert not [f for f in result.findings if f.severity.name == "ERROR"]
