# Settings

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page holds the settings of one build: `fr.settings`, the consumer's TOML file, the paper per drawing type, and the `SettingsError` a wrong key raises. Every build uses our defaults until you pass `settings=`.

## `fr.settings`

`fr.settings(path=None, *, paper=None)` returns a `fr.Settings`, a frozen value. With no arguments it gives our defaults. `path` names a TOML file of your own settings. `paper` maps a `fr.PageKind` to a paper's name.

`fr.Settings` has seven named fields. `paper` holds the paper formats and the default paper. `paper_by_kind` holds the paper for each drawing type. `grid` holds `module_mm`. `font` is empty for our font, else the name and the two font files. `pdf`, `look` and `layout` hold the other tables. Every other table is read with `Settings.table(name)`; a build reads `lines`, `dash` and `font.heights` that way.

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

Every key of `[pdf]`, `[look]` and `[layout]` is overridable, key by key. A key is refused for three reasons: it is unknown, its type differs from ours, or it is library data or a Python-only choice. `[layout]` holds the placement numbers; `contact_tables` is one of them, false by default.

```toml
[layout]
row_gap = 32

[pdf]
list_share_pct = 30
```

The two values change and nothing else does.

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text("[layout]\nrow_gap = 32\n[pdf]\nlist_share_pct = 30\n", encoding="utf-8")
    s = fr.settings(file)

assert s.layout["row_gap"] == 32
assert s.pdf["list_share_pct"] == 30
assert {**s.layout, "row_gap": 24} == dict(fr.settings().layout)
assert s.look == fr.settings().look
assert s.table("look") == s.look  # any merged table by name
```

## The grid and the font

One build has one grid and one font. `[grid]` takes `module_mm` alone, the millimetres of one grid module. The divisions and the wire pitches are library data, and a key for one raises.

`[font]` takes the regular and the bold TrueType file, in that order. Each path is relative to the settings file. The widths of the text come from the files themselves. The text sizes are the `[font.heights]` table, below. The build fails with `SettingsError` when a symbol's fixed text no longer fits its body in the new font, and the PDF is set in the font you name.

```toml
# fransys.toml
[grid]
module_mm = 2.0

[font]
name = "Liberation Sans Narrow"
files = ["fonts/LiberationSansNarrow-Regular.ttf", "fonts/LiberationSansNarrow-Bold.ttf"]
```

`[font.heights]` sets a capital height in mm by role (`smallest`, `body`, `heading_2`, `heading_1`). `[lines]` sets a stroke width in mm (`normal`, `thick`, `rule`). `[dash]` sets a dash pattern in mm (`dashed`, `dash_dot`, `long`). Each key replaces ours alone and the rest keep ours. A key we do not have raises `SettingsError`, naming the keys that exist.

```toml
[font.heights]
body = 3.0

[lines]
rule = 0.3
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

## The reference signs

`[reference]` holds the signs of a printed reference: `page_prefix`, `cell_sep`, `location_sign`, `set_sep` and `width_sample`. Our defaults print `p3:A1`, `+A1` and `2.3`. An empty `page_prefix` prints `3:A1`.

```toml
[reference]
page_prefix = ""
cell_sep = "."
```

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[reference]\npage_prefix = ""\ncell_sep = "."\n', encoding="utf-8")
    s = fr.settings(file)

assert s.table("reference")["cell_sep"] == "."
assert s.table("reference")["location_sign"] == "+"
```

## The frame labels

`[frame]` names the labels of the page frame. `row_labels` and `column_labels` take `letters` or `numbers`. `row_order` takes `top_down` or `bottom_up`. Any other value raises `SettingsError`.

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[frame]\nrow_order = "bottom_up"\n', encoding="utf-8")
    assert fr.settings(file).table("frame")["row_order"] == "bottom_up"
```

## Stub, wire label and harness text

`[stub]` holds the two arrows and the two joins of an off-page stub. `[wire_label]` holds the `separator` between the two ends and `show_ends`. `[harness]` holds the `branch_sep` of a harness line.

```python
stub = fr.settings().table("stub")
assert stub["port_sep"] == ":"
assert fr.settings().table("harness")["branch_sep"] == "."
```

## The title block and the revision

`[title_block]` lists the `fields` the block prints, in order, with the `band_mm` height. A field left out is not printed. `[revision]` sets the `format` of a printed revision, such as `{version}.{revision}`, the `date_format` and `initials_required`.

`[revision_table]` lists the `columns` of the revision table by their keys in `[words]`. Its `description_mm` is the one wrapping column.

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[revision]\nformat = "{version}-{revision}"\n', encoding="utf-8")
    s = fr.settings(file)

assert s.table("revision")["format"] == "{version}-{revision}"
assert s.table("revision")["initials_required"] is True
```

## The words

`[words]` holds the words the drawings and lists print, such as `side_a`, `pin`, `spare`, `no` and `nc`, and the page headings. The PLC list prints the signal words `signal_di`, `signal_do`, `signal_ai_ma`, `signal_ai_v`, `signal_ao_ma`, `signal_ao_v`, `signal_rtd` and `signal_relay_do`. Each word has one key. A key you leave out keeps our word.

```toml
[words]
side_a = "Side A (field)"
```

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[words]\nside_a = "Side A (field)"\n', encoding="utf-8")
    s = fr.settings(file)

assert s.table("words")["side_a"] == "Side A (field)"
assert s.table("words")["side_b"] == "Side B"
```

## `SettingsError`

`fr.settings` raises `fr.SettingsError` for a file that is missing, is not TOML, or has a key Fransys does not know. It also raises for a value of another type than ours, for library data in a TOML file, and for a paper name that is not a format. Its message names the file, the key and the keys known there.

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
    later.write_text("[layout]\nfrobnicate = 1\n", encoding="utf-8")
    try:
        fr.settings(later)
    except fr.SettingsError as e:
        assert "is not a setting; known:" in str(e)
    else:
        raise AssertionError("expected SettingsError")

    wrong = Path(folder) / "wrong.toml"
    wrong.write_text("[layout]\ncontact_tables = 1\n", encoding="utf-8")
    try:
        fr.settings(wrong)
    except fr.SettingsError as e:
        assert "must be true or false" in str(e)
    else:
        raise AssertionError("expected SettingsError")
```

## `BuildResult.settings`

`fr.build` returns a `BuildResult`, and its `settings` field holds the `fr.Settings` the build used. Without `settings=` it holds our defaults.
