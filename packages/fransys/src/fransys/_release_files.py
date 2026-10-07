"""Released files never change (WORKFLOW-BLOCKS W5, W6): `verify` re-hashes every release folder."""

import hashlib
from pathlib import Path

from fransys_model.kernel import Finding, Severity

from ._release_reader import (
    file_bytes,
    folder_files,
    has_manifest,
    manifest_fields,
    read_release,
    release_folders,
)

# Text exports only: a Windows git checkout may turn their LF into CRLF (W6); a PDF never is.
_TEXT_SUFFIXES = frozenset({".csv", ".json", ".md", ".xml", ".html", ".txt"})


def _finding(code: str, release_name: str, folder: Path, detail: str) -> Finding:
    return Finding(
        code=code,
        severity=Severity.ERROR,
        subjects=(),
        message=f"{release_name} {folder.name}: {detail}",
    )


def _same(data: bytes, relative: str, expected: str) -> bool:
    """Whether `data` hashes to `expected`; a text file also passes with CRLF read as LF."""
    if hashlib.sha256(data).hexdigest() == expected:
        return True
    if Path(relative).suffix not in _TEXT_SUFFIXES:
        return False
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == expected


def _manifest_finding(folder: Path) -> Finding | None:
    """The finding for a missing or broken manifest, else `None`."""
    name = folder.parent.name
    if not has_manifest(folder):
        return _finding("RELEASE_FILE_MISSING", name, folder, "baseline/manifest.json")
    try:
        manifest_fields(folder)
    except ValueError:
        return _finding("RELEASE_FILE_CHANGED", name, folder, "baseline/manifest.json")
    return None


def _folder_findings(folder: Path) -> list[Finding]:
    """Every missing, changed and unlisted file of one release folder."""
    bad_manifest = _manifest_finding(folder)
    if bad_manifest is not None:
        return [bad_manifest]
    release = read_release(folder)
    findings: list[Finding] = []
    for relative, expected in release.files:
        data = file_bytes(folder, relative)
        if data is None:
            findings.append(_finding("RELEASE_FILE_MISSING", release.name, folder, relative))
        elif not _same(data, relative, expected):
            findings.append(_finding("RELEASE_FILE_CHANGED", release.name, folder, relative))
    listed = {relative for relative, _ in release.files} | {"baseline/manifest.json"}
    for relative in sorted(folder_files(folder) - listed):
        detail = f"{relative} (not in the manifest)"
        findings.append(_finding("RELEASE_FILE_CHANGED", release.name, folder, detail))
    return findings


def release_file_findings(baselines: Path) -> tuple[Finding, ...]:
    """`RELEASE_FILE_CHANGED` and `RELEASE_FILE_MISSING` over every release under `baselines`."""
    return tuple(f for folder in release_folders(baselines) for f in _folder_findings(folder))
