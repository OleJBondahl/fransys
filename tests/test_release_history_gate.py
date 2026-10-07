"""`RELEASE_HISTORY_UNRELEASED`: a history entry names a revision never released (W7).

Acceptance 5, 6 and 12. Dates run in the order the entries are listed, so history order is the
listed order unless a test says otherwise.
"""

import sys
from pathlib import Path

import fransys as fr
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_system, release_board


def _history(*pairs):
    """`(version, revision, date)` triples with ascending dates."""
    return [(v, r, f"2026-02-{i:02d}") for i, (v, r) in enumerate(pairs, 1)]


def _refused(into, version, revision, pairs):
    with pytest.raises(fr.BuildErrors) as exc:
        release_board(into, version=version, revision=revision, history=_history(*pairs))
    assert {f.code for f in exc.value.findings} == {"RELEASE_HISTORY_UNRELEASED"}
    return sorted(f.message for f in exc.value.findings)


def test_the_worked_example_free_unreleased_then_refused_then_version_two(tmp_path):
    """Entries 1.1 and 1.2 are an old register's; 1.4 has no folder; 2.1 and 2.2 come after 1.3."""
    release_board(tmp_path, revision=3, history=_history((1, 1), (1, 2), (1, 3)))
    messages = _refused(tmp_path, 1, 5, [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5)])
    assert len(messages) == 1
    assert "1.4" in messages[0]
    messages = _refused(tmp_path, 2, 3, [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)])
    assert [("2.1" in m, "2.2" in m) for m in messages] == [(True, False), (False, True)]


def test_a_first_release_leaves_every_entry_free(tmp_path):
    folder = release_board(tmp_path, revision=3, history=_history((1, 1), (1, 2), (1, 3)))
    assert folder.name == "1.3"


def test_an_entry_looks_for_its_folder_in_its_own_version(tmp_path):
    """Folders 1.1 and 1.2 exist; entry 2.1 has no folder of its own, so it is refused."""
    release_board(tmp_path, revision=1, history=_history((1, 1)))
    release_board(tmp_path, revision=2, history=_history((1, 1), (1, 2)))
    messages = _refused(tmp_path, 2, 4, [(1, 1), (1, 2), (2, 1), (2, 4)])
    assert len(messages) == 1
    assert "2.1" in messages[0]


def test_entries_dated_before_the_first_release_stay_free_in_every_version(tmp_path):
    """Acceptance 12: 1.1, 1.2, 2.1, 2.2 dated before the first release 1.3; then 1.4 releases."""
    old = [(1, 1, "2025-01-01"), (1, 2, "2025-01-02"), (2, 1, "2025-01-03"), (2, 2, "2025-01-04")]
    release_board(tmp_path, revision=3, history=[*old, (1, 3, "2026-02-01")])
    folder = release_board(
        tmp_path, revision=4, history=[*old, (1, 3, "2026-02-01"), (1, 4, "2026-02-02")]
    )
    assert folder.name == "1.4"


def test_a_system_release_checks_the_projects_own_history(tmp_path):
    first = build_system(history=_history((1, 1)))
    fr.release(first, tmp_path)
    second = build_system(revision=3, history=_history((1, 1), (1, 2), (1, 3)))
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(second, tmp_path)
    assert {f.code for f in exc.value.findings} == {"RELEASE_HISTORY_UNRELEASED"}
