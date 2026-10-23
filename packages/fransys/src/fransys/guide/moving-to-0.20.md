# Moving to 0.20

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

This page lists each call that 0.20 adds or changes, with the old spelling and the new one.

## A baseline cut by an older fransys

`fr.verify` compares a stored listing under the rules of the `fransys` that cut it. When a later
release printed a rule differently, it gives `BASELINE_RULES_MOVED` (INFO) for that release, and
`fr.release` refuses over it. `fr.rebaseline` is the new call that clears it: it re-cuts the stored
`listing.json` and the manifest under today's rules and leaves every export as it was.

Run `fr.rebaseline(result, Path("releases"))` once and commit the rewritten files. The worked example
is in `build.md`, after "Checking a baseline stays true".

## A finding carries its fix

`fr.Finding` has a new field `fix`: the text that clears it, `<valid values>. Write: <corrected call>`. `fr.report` prints the finding's own `fix`, and `BuildErrors.findings` holds the same rows, so a test reads `exc.findings[0].fix`. `LABEL_UNPLACED` is now INFO (a Fransys defect, send the smallest model). A `fr.Finding(...)` you build yourself with severity ERROR or WARNING must pass `fix=`.

## Renames in the change list

A listing now carries item keys (version 2), so the change list follows a rename: "Renamed -A1 → -A2"
replaces a removal and an addition, and `changes.csv` writes `renamed` in the `change`
column. A release cut before 0.20 has no keys: its diff pairs by name and `CHANGES_BY_NAME` says
so. `fr.rebaseline` writes version 2.

## A derive row type renamed

`fr.derive.BridgePiece`, the row that holds one jumper-bridge image, is now `fr.derive.BridgePieceRow`,
so it no longer shares a name with the symbol's `electrical_symbols.BridgePiece` (`"line"` or `"tick"`).
No alias keeps the old name. Only code that names the type changes; the fields are as they were.

`DocumentScope.bom_top_level` is now `DocumentScope.top_level`.
