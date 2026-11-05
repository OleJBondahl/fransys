# Settings

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page holds the settings of one build: `fr.settings`, the consumer's TOML file, the paper per drawing type, and the `SettingsError` a wrong key raises. Every build uses our defaults until you pass `settings=`.

`SettingsError` and `BuildFailedError` share the base `FransysError`, which is also a bad argument to a facade call. It is a `TypeError` and a `ValueError`, so `except TypeError` and `except ValueError` still catch it.

## `fr.settings`

`fr.settings(path=None, *, paper=None)` returns a `fr.Settings`, a frozen value. With no arguments it gives our defaults. `path` names a TOML file of your own settings. `paper` maps a `fr.PageKind` to a paper's name.

`fr.Settings` has six named fields. `paper` holds the paper formats and the default paper. `paper_by_kind` holds the paper for each drawing type. `font` is empty for our font, else the name and the two font files. `pdf`, `look` and `layout` hold our own values, which a file cannot change. Every other table is read with `Settings.table(name)`.

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
from collections.abc import Mapping
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

A project sets only words, lists and export. The engine numbers (`[layout]`, `[profile]`), the PDF numbers (`[pdf]`), the look (`[look]`) and the stroke widths and dash patterns (`[lines]`, `[dash]`) are ours and fixed. A file that names one of those tables raises `SettingsError`; delete the table.

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text("[layout]\nrow_gap = 32\n", encoding="utf-8")
    try:
        fr.settings(file)
    except fr.SettingsError as e:
        assert "[layout] is fixed in 0.22; remove it from your settings" in str(e)
    else:
        raise AssertionError("expected SettingsError")

assert fr.settings().layout["row_gap"] == 24
```

## The font

One build has one font. The grid is the library's fixed 2.5 mm module, so a `[grid]` table raises; delete it.

`[font]` takes the regular and the bold TrueType file, in that order. Each path is relative to the settings file. The widths of the text come from the files themselves. The text sizes are the library's fixed heights: a `[font.heights]` table is refused. The build fails with `SettingsError` when a symbol's fixed text no longer fits its body in the new font, and the PDF is set in the font you name.

```toml
# fransys.toml
[font]
name = "Liberation Sans Narrow"
files = ["fonts/LiberationSansNarrow-Regular.ttf", "fonts/LiberationSansNarrow-Bold.ttf"]
```

Today's schematic engine keeps the built-in font. The keys apply to the drawings of the new engine, and a build with one set gives one `SETTING_NEW_ENGINE_ONLY` WARNING per key; the WARNING goes when the old engine does (MODEL-TEXT).

A `[grid]` table shows the reason.

```python
with tempfile.TemporaryDirectory() as folder:
    grid = Path(folder) / "fransys.toml"
    grid.write_text("[grid]\nmodule_mm = 2.0\n", encoding="utf-8")
    try:
        fr.settings(grid)
    except fr.SettingsError as e:
        assert "the grid is the library's fixed 2.5 mm" in str(e)
    else:
        raise AssertionError("expected SettingsError")
```

## The paper per drawing type

`paper` maps a drawing type to a paper's name, such as `{fr.PageKind.BLOCK_DIAGRAM: "A2"}`. The formats are closed: `A3` and `A2`, all landscape. A TOML `[paper.formats]` table, a portrait sheet or any other size is refused (`SHEET_FORMAT_NOT_SUPPORTED` for an authored sheet). Every PDF that shows that drawing type shows the same layout. Our default puts the block diagram on A2 and every other drawing on A3.

Name the paper per drawing type in Python only. A per-kind key in a TOML file raises.

```python
s = fr.settings(paper={fr.PageKind.BLOCK_DIAGRAM: "A3"})
assert s.paper_by_kind[fr.PageKind.BLOCK_DIAGRAM] == "A3"
assert fr.settings().paper_by_kind[fr.PageKind.BLOCK_DIAGRAM] == "A2"
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

## The lists

`[lists.<name>]` holds the columns of one list: `bom`, `plc`, `wires`, `designations`, `cables`, `cores`, `terminal`, `connectors` or `contents`. Each `[[lists.<name>.columns]]` row has the row `field` it prints, the `pdf` word that heads it in the PDF and the `csv` word that heads it in the CSV file. Both words are keys of `[words]`. A list's `pdf_columns` names the fields its PDF prints, when that is fewer than the CSV prints. A consumer's rows replace the list's columns as a whole.

```toml
[[lists.bom.columns]]
field = "mpn"
pdf = "head_mpn"
csv = "csv_mpn"

[[lists.bom.columns]]
field = "count"
pdf = "head_count"
csv = "csv_count"
```

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    columns = '[[lists.bom.columns]]\nfield = "mpn"\npdf = "head_mpn"\ncsv = "csv_mpn"\n'
    file.write_text(columns, encoding="utf-8")
    s = fr.settings(file)

bom = s.table("lists")["bom"]
assert isinstance(bom, Mapping)
assert [row["field"] for row in bom["columns"]] == ["mpn"]
```

## The export files

`[export]` sets which files `fr.write` makes and how it names, places and encodes them. `reports` lists the whole-model reports, in order: `bom`, `plc`, `wires`, `designations`, `cables` and `cores`. A name outside those six raises `SettingsError`. `name_join` joins the prefix, the kind and the fragment of a file name, `version_sign` sits before the version, and `ref_sign` replaces each sign of a designation, so `=A1+C1-K1` gives `A1-C1-K1`.

`data_dir` is the folder of the files that end in one of `data_suffixes`. The CSV files follow `csv_delimiter`, `csv_encoding`, `csv_quoting` (`minimal`, `all`, `nonnumeric` or `none`) and `csv_newline`. Only a `.csv` file takes `csv_encoding`; the others stay UTF-8. `fr.derive.export_form_of(model)` gives the record a build holds.

```toml
[export]
reports = ["bom", "wires"]
csv_delimiter = ";"
csv_encoding = "utf-8-sig"
```

```python
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / "fransys.toml"
    file.write_text('[export]\ncsv_delimiter = ";"\n', encoding="utf-8")
    s = fr.settings(file)

assert s.table("export")["csv_delimiter"] == ";"
assert s.table("export")["data_dir"] == "data"
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
    later.write_text('[export]\nfrobnicate = 1\n', encoding="utf-8")
    try:
        fr.settings(later)
    except fr.SettingsError as e:
        assert "is not a setting; known:" in str(e)
    else:
        raise AssertionError("expected SettingsError")
```

## `BuildResult.settings`

`fr.build` returns a `BuildResult`, and its `settings` field holds the `fr.Settings` the build used. Without `settings=` it holds our defaults.
