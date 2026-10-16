"""Cable blocks group into part runs: parts sorted by number, part-less blocks last (pdf-0020)."""

from fransys_model.derive import NO_PART, CableBlockRef, cable_runs


def _block(key: str, mpn: str) -> CableBlockRef:
    return CableBlockRef(key=key, mpn=mpn, line=f"line {key}")


def test_parts_sorted_blocks_in_given_order_part_less_last():
    runs = cable_runs([_block("b1", "B"), _block("a1", "A"), _block("n1", ""), _block("a2", "A")])
    assert [run.heading for run in runs] == ["A", "B", NO_PART]
    assert runs[0].blocks == (_block("a1", "A"), _block("a2", "A"))
    assert runs[1].blocks == (_block("b1", "B"),)
    assert runs[2].blocks == (_block("n1", ""),)


def test_no_blocks_no_runs():
    assert cable_runs([]) == ()


def test_all_part_less_one_run_headed_no_part():
    runs = cable_runs([_block("n1", ""), _block("n2", "")])
    assert [run.heading for run in runs] == [NO_PART]
    assert runs[0].blocks == (_block("n1", ""), _block("n2", ""))
