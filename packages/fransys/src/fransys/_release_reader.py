"""The one reader of release folders : no other facade code opens a file in one.

A release folder is `<root>/<name>/<version>.<revision>/`. Reads here are text for the stored
listing and numbering (universal newlines, so a CRLF checkout reads like LF) and bytes for hashes.
"""

import dataclasses
import json
import re
from typing import Any, cast
lazy from pathlib import Path

from fransys_model.derive import baseline, numbering_pins
from fransys_model.derive.baseline import StoredRelease, StoredReleases

_REVISION_DIR_RE = re.compile(r"[0-9]+\.[0-9]+")
# Every file a release folder holds beside its exports, by role, as its path in the folder (R07).
BASELINE_FILES = {
    "listing": "baseline/listing.json",
    "model": "baseline/model.json",
    "numbering": "baseline/numbering.json",
    "manifest": "baseline/manifest.json",
    "changes_md": "changes.md",
    "changes_csv": "changes.csv",
}


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ReleasePin:
    """A release nested in another, as its manifest records it."""

    name: str
    version: int
    revision: int
    listing_digest: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Release:
    """One release folder under a releases root, read from its manifest.

    `name`, `version` and `revision` come from the folder's path. `interface`, `listing_digest`,
    `nested` and `files` (path, sha256 pairs) come from `baseline/manifest.json`; a folder with no
    manifest has them empty. `path` is the folder.
    """

    name: str
    version: int
    revision: int
    interface: str
    listing_digest: str
    nested: tuple[ReleasePin, ...]
    files: tuple[tuple[str, str], ...]
    path: Path


def revision_dirs(parent: Path) -> tuple[Path, ...]:
    """The `<version>.<revision>` folders of `parent`, in integer order; none when it is missing."""
    if not parent.is_dir():
        return ()
    found = [p for p in parent.iterdir() if p.is_dir() and _REVISION_DIR_RE.fullmatch(p.name)]
    return tuple(sorted(found, key=_folder_order))


def _folder_order(folder: Path) -> tuple[int, int]:
    version, revision = folder.name.split(".")
    return int(version), int(revision)


def manifest_path(folder: Path) -> Path:
    """Where `folder`'s manifest is, whether or not it exists."""
    return folder / BASELINE_FILES["manifest"]


def has_manifest(folder: Path) -> bool:
    """Whether `folder` has a `baseline/manifest.json`."""
    return manifest_path(folder).is_file()


def _text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def stored_listing(folder: Path) -> str | None:
    """`folder`'s stored `baseline/listing.json` text, or `None` when it has none."""
    return _text(folder / BASELINE_FILES["listing"])


def stored_numbering(folder: Path) -> str | None:
    """`folder`'s stored `baseline/numbering.json` text, or `None` when it has none."""
    return _text(folder / BASELINE_FILES["numbering"])


def listed_siblings(parent: Path) -> tuple[tuple[Path, str], ...]:
    """Each `<version>.<revision>` folder of `parent` that has a stored listing, with its text."""
    pairs = ((folder, stored_listing(folder)) for folder in revision_dirs(parent))
    return tuple((folder, text) for folder, text in pairs if text is not None)


def file_bytes(folder: Path, relative: str) -> bytes | None:
    """The raw bytes of `relative` (a manifest path) inside `folder`, or `None` when it is gone."""
    path = folder / relative
    return path.read_bytes() if path.is_file() else None


def folder_files(folder: Path) -> frozenset[str]:
    """Every file below `folder`, as `/`-separated paths relative to it."""
    return frozenset(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())


def released_revisions(parent: Path) -> frozenset[tuple[int, int]]:
    """`(version, revision)` of every folder of `parent` that holds a stored listing."""
    return frozenset(_folder_order(folder) for folder, _ in listed_siblings(parent))


def _broken(folder: Path, why: str) -> ValueError:
    return ValueError(f"{manifest_path(folder)}: {why}")


def _pin(folder: Path, row: Any) -> ReleasePin:  # noqa: ANN401 -- a JSON value, checked below
    try:
        return ReleasePin(
            name=_typed(row["name"], str),
            version=_typed(row["version"], int),
            revision=_typed(row["revision"], int),
            listing_digest=_typed(row["listing_digest"], str),
        )
    except (KeyError, TypeError) as error:
        raise _broken(folder, f"a nested entry is malformed ({error!r})") from error


def _typed[T](value: object, kind: type[T]) -> T:
    if type(value) is not kind:
        raise TypeError(value)
    return cast("T", value)


def _file_pair(folder: Path, row: Any) -> tuple[str, str]:  # noqa: ANN401 -- a JSON value
    try:
        return _typed(row["path"], str), _typed(row["sha256"], str)
    except (KeyError, TypeError) as error:
        raise _broken(folder, f"a files entry is malformed ({error!r})") from error


def manifest_data(folder: Path) -> dict[str, Any]:
    """`folder`'s manifest, parsed whole.

    Raises `ValueError` naming the manifest when it is missing or does not parse to an object.
    """
    try:
        data = json.loads(manifest_path(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise _broken(folder, f"cannot be read ({error!r})") from error
    if not isinstance(data, dict):
        raise _broken(folder, "is not a JSON object")
    return data


def manifest_readable(folder: Path) -> bool:
    """Whether `folder` has a manifest that parses to a JSON object."""
    try:
        manifest_data(folder)
    except ValueError:
        return False
    return True


def _recut_by(data: dict[str, Any]) -> str | None:
    """The `cut_by` of the last `rebaselined` record that re-cut the listing, else `None`."""
    for record in reversed(data.get("rebaselined", [])):
        cut_by = record.get("cut_by")
        if record.get("reason") == "rules" and isinstance(cut_by, str):
            return cut_by
    return None


def stored_fransys_version(folder: Path) -> str | None:
    """The `fransys` whose rules `folder`'s listing holds: its last re-cut, else `packages`' entry.

    `None` when the manifest is missing, broken or names no `fransys`.
    """
    if not has_manifest(folder):
        return None
    try:
        data = manifest_data(folder)
        if (recut := _recut_by(data)) is not None:
            return recut
        rows = data["packages"]
        return next(_typed(r["version"], str) for r in rows if r["name"] == "fransys")
    except ValueError, KeyError, TypeError, StopIteration, AttributeError:
        return None


def manifest_fields(
    folder: Path,
) -> tuple[str, str, tuple[ReleasePin, ...], tuple[tuple[str, str], ...]]:
    """`(interface, listing_digest, nested, files)` of `folder`'s manifest.

    Raises `ValueError` naming the manifest when it does not parse or lacks a promised key.
    The manifest must exist; `read_release` handles a folder without one.
    """
    try:
        data = json.loads(manifest_path(folder).read_text(encoding="utf-8"))
        interface = _typed(data["unit"]["interface"], str)
        digest = _typed(data["listing_digest"], str)
        nested_rows, file_rows = data["nested"], data["files"]
    except (ValueError, KeyError, TypeError) as error:
        raise _broken(folder, f"cannot be read ({error!r})") from error
    nested = tuple(_pin(folder, row) for row in nested_rows)
    return interface, digest, nested, tuple(_file_pair(folder, row) for row in file_rows)


def read_release(folder: Path) -> Release:
    """The `Release` of one `<root>/<name>/<version>.<revision>` folder.

    Raises `ValueError` naming the manifest when it exists and is broken.
    """
    version, revision = _folder_order(folder)
    identity = {"name": folder.parent.name, "version": version, "revision": revision}
    if not has_manifest(folder):
        return Release(
            **identity, interface="", listing_digest="", nested=(), files=(), path=folder
        )
    interface, digest, nested, files = manifest_fields(folder)
    return Release(
        **identity,
        interface=interface,
        listing_digest=digest,
        nested=nested,
        files=files,
        path=folder,
    )


def release_folders(root: Path) -> tuple[Path, ...]:
    """Every release folder under `root`, in (name, version, revision) order."""
    if not root.is_dir():
        return ()
    names = sorted(p for p in root.iterdir() if p.is_dir())
    return tuple(folder for name in names for folder in revision_dirs(name))


def releases(root: Path) -> tuple[Release, ...]:
    """Output: every release folder under `root`, read from its manifest.

    They come in name, version, revision order.

    `root` holds `<name>/<version>.<revision>/` folders, as `fr.release` writes them. Versions and
    revisions sort as integers. A folder with no manifest is listed with empty `interface`,
    `listing_digest`, `nested` and `files`. A missing `root` gives `()`.

    Raises:
        ValueError: a manifest does not parse or lacks a key; the message names its path.

    Does not write files, check a file's hash or read any model.
    """
    return tuple(read_release(folder) for folder in release_folders(root))


def read_stored(parent: Path) -> StoredReleases:
    """Every release folder of `parent` (`<into>/<name>/`) that has a stored listing, read once.

    The one fill of `StoredReleases`: derive chooses the previous release and the pin source.
    """
    stored = []
    for folder, listing_text in listed_siblings(parent):
        numbering_text = stored_numbering(folder)
        numbering = None if numbering_text is None else numbering_pins.loads(numbering_text)
        stored.append(
            StoredRelease(
                folder=folder.name,
                listing=baseline.loads(listing_text),
                numbering=numbering,
            )
        )
    return StoredReleases(releases=tuple(stored))
