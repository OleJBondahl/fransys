# Moving to 0.20

This page lists each call that 0.20 adds or changes, with the old spelling and the new one.

## A baseline cut by an older fransys

`fr.verify` compares a stored listing under the rules of the `fransys` that cut it. When a later
release printed a rule differently, it gives `BASELINE_RULES_MOVED` (INFO) for that release, and
`fr.release` refuses over it. `fr.rebaseline` is the new call that clears it: it re-cuts the stored
`listing.json` and the manifest under today's rules and leaves every export as it was.

Run `fr.rebaseline(result, Path("releases"))` once and commit the rewritten files. The worked example
is in `build.md`, after "Checking a baseline stays true".

## Renames in the change list

A listing now carries item keys (version 2), so the change list follows a rename: "Renamed -A1 → -A2"
replaces a removal and an addition, and `changes.csv` writes `renamed` in the `change`
column. A release cut before 0.20 has no keys: its diff pairs by name and `CHANGES_BY_NAME` says
so. `fr.rebaseline` writes version 2.
