# Settings

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page holds the settings of one build: `fr.settings`, the consumer's TOML file, the paper per drawing type, and the `SettingsError` a wrong key raises. Every build uses our defaults until you pass `settings=`.

## `fr.settings`

`fr.settings(path=None, *, paper=None)` returns a `fr.Settings`, a frozen value. With no arguments it gives our defaults. `path` names a TOML file of your own settings. `paper` maps a `fr.PageKind` to a paper's name.

`fr.Settings` has seven fields. `paper` holds the paper formats and the default paper. `paper_by_kind` holds the paper for each drawing type. `grid` holds `module_mm`. `font` is empty for our font, else the name and the two font files. `pdf`, `look` and `layout` hold the other tables. A build reads `paper`, `paper_by_kind`, `grid` and `font` today.

```python
import fransys as fr

base = fr.settings()
assert base.paper["default"] == "A3"
assert base.paper_by_kind[fr.PageKind.BLOCK_DIAGRAM] == "A2"
```

## The TOML file

A consumer's file names only what differs from our defaults. The merge is key by key. A key the file gives replaces ours. A key it leaves out keeps our value. A file that sets only `default` changes only `default`.

A consumer's project might hold this `fransys.toml`:

```toml
# fransys.toml: only what differs from our defaults
[paper]
default = "A2"
```

The build script reads the file and passes the result to the build. The script below writes the same file into a temporary folder, so it runs as it stands.

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[paper]\ndefault = "A2"\n', encoding="utf-8")
    s = fr.settings(file, paper={fr.PageKind.BLOCK_DIAGRAM: "A2"})

assert s.paper["default"] == "A2"

d = fr.design("demo_parts")
d.device("X1", "DEMO-CONN-2P")
result = fr.build(d, settings=s)
assert result.settings is s
```

`[layout]` takes one key today, `contact_tables`, true or false. It is false: a coil's contact table is not drawn, because a table with no room beside its coil is not yet placed. Set it to true to draw the tables; one that finds no free corner raises the `ANNEX_UNPLACED` warning.

```toml
[layout]
contact_tables = true
```

Any other `[layout]` key arrives with SETTINGS-B. A `[pdf]` or `[look]` key arrives with SETTINGS-LOOK. Until then such a key raises `SettingsError`.

## The grid and the font

One build has one grid and one font. `[grid]` takes `module_mm` alone, the millimetres of one grid module. The divisions and the wire pitches are library data, and a key for one raises.

`[font]` takes the regular and the bold TrueType file, in that order. Each path is relative to the settings file. The widths of the text come from the files themselves. The text sizes stay ours: a `heights` key raises. The build fails with `SettingsError` when a symbol's fixed text no longer fits its body in the new font, and the PDF is set in the font you name.

```toml
# fransys.toml
[grid]
module_mm = 2.0

[font]
name = "Liberation Sans Narrow"
files = ["fonts/LiberationSansNarrow-Regular.ttf", "fonts/LiberationSansNarrow-Bold.ttf"]
```

Today's schematic engine keeps the built-in grid and font. The keys apply to the drawings of the new engine, and a build with either set gives one `SETTING_NEW_ENGINE_ONLY` WARNING per key; the WARNING goes when the old engine does (MODEL-TEXT).

A wrong grid key shows the reason.

```python
with tempfile.TemporaryDirectory() as folder:
    grid = Path(folder) / "fransys.toml"
    grid.write_text("[grid]\nmodule_mm = 2.0\n", encoding="utf-8")
    assert fr.settings(grid).grid["module_mm"] == 2.0
    grid.write_text("[grid]\nwire_pitch = 4\n", encoding="utf-8")
    try:
        fr.settings(grid)
    except fr.SettingsError as e:
        assert "is library data" in str(e)
    else:
        raise AssertionError("expected SettingsError")
```

## The paper per drawing type

`paper` maps a drawing type to a paper's name, such as `{fr.PageKind.BLOCK_DIAGRAM: "A2"}`. Only the formats `A3` and `A2` exist today. Every PDF that shows that drawing type shows the same layout. Our default puts the block diagram on A2 and every other drawing on A3.

Name the paper per drawing type in Python only. A per-kind key in a TOML file raises.

```python
s = fr.settings(paper={fr.PageKind.BLOCK_DIAGRAM: "A3"})
assert s.paper_by_kind[fr.PageKind.BLOCK_DIAGRAM] == "A3"
assert fr.settings().paper_by_kind[fr.PageKind.BLOCK_DIAGRAM] == "A2"
```

## `SettingsError`

`fr.settings` raises `fr.SettingsError` for a file that is missing, is not TOML, or has a key Fransys does not know. It also raises for a key whose reader has not landed, and for a paper name that is not a format. Its message names the file, the key and the keys known there.

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as folder:
    typo = Path(folder) / "fransys.toml"
    typo.write_text('[paper]\ndefualt = "A2"\n', encoding="utf-8")
    try:
        fr.settings(typo)
    except fr.SettingsError as e:
        assert "known: default, formats" in str(e)
    else:
        raise AssertionError("expected SettingsError")

    later = Path(folder) / "later.toml"
    later.write_text("[layout]\nrow_gap = 32\n", encoding="utf-8")
    try:
        fr.settings(later)
    except fr.SettingsError as e:
        assert "is not read yet: it arrives with SETTINGS-B" in str(e)
    else:
        raise AssertionError("expected SettingsError")
```

## `BuildResult.settings`

`fr.build` returns a `BuildResult`, and its `settings` field holds the `fr.Settings` the build used. Without `settings=` it holds our defaults.
