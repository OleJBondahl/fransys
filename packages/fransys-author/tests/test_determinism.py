"""Two runs give equal drafts; statement order changes no id, except A7's terminal index."""

from fransys_model.kernel import freeze, merge


def _build(d):
    c1 = d.location("C1", "cabinet")
    sup = d.group("SUP", "supply")
    x1 = d.strip("X1", at=c1)
    t1 = x1.terminal("TEST-TB", group=sup)
    t2 = x1.terminal("TEST-TB", group=sup)
    k1 = d.item("TEST-RLY-2CO", name="run", at=c1, group=sup)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], t2.inner)
    d.chain(t1, k1.fn("coil"), t2)


def test_two_runs_from_the_same_call_site_give_equal_models(parts):
    from fransys_author import Design

    a = Design(parts)
    _build(a)
    b = Design(parts)
    _build(b)
    model_a = freeze(merge(parts, a.draft()))
    model_b = freeze(merge(parts, b.draft()))
    assert model_a == model_b
    assert model_a.digest == model_b.digest


def test_two_runs_can_disagree_when_content_differs(parts):
    """Can-fail proof: a real content change does break model equality."""
    from fransys_author import Design

    a = Design(parts)
    _build(a)

    b = Design(parts)
    c1 = b.location("C1", "cabinet")
    sup = b.group("SUP", "supply")
    x1 = b.strip("X1", at=c1)
    t1 = x1.terminal("TEST-TB", group=sup)
    t2 = x1.terminal("TEST-TB", group=sup)
    k1 = b.item("TEST-RLY-2CO", name="run", at=c1, group=sup)
    wire = b.wiring(colour="BU", gauge="0.75")
    wire(t1.inner, k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], t2.inner)
    # no chain here: the deliberate difference

    model_a = freeze(merge(parts, a.draft()))
    model_b = freeze(merge(parts, b.draft()))
    assert model_a != model_b


def test_statement_order_does_not_change_any_id(parts):
    """Two independent groups authored in opposite order give the same ids and digest."""
    from fransys_author import Design

    forward = Design(parts)
    c1 = forward.location("C1", "cabinet")
    sup = forward.group("SUP")
    p1 = forward.group("P1")
    forward.item("TEST-RLY-2CO", tag="K1", at=c1, group=sup)
    forward.item("TEST-RLY-2CO", tag="K2", at=c1, group=p1)

    backward = Design(parts)
    c1b = backward.location("C1", "cabinet")
    p1b = backward.group("P1")
    supb = backward.group("SUP")
    backward.item("TEST-RLY-2CO", tag="K2", at=c1b, group=p1b)
    backward.item("TEST-RLY-2CO", tag="K1", at=c1b, group=supb)

    model_forward = freeze(merge(parts, forward.draft()))
    model_backward = freeze(merge(parts, backward.draft()))
    assert model_forward.digest == model_backward.digest


def test_terminal_index_is_the_one_exception_call_order_counts(parts):
    """Spec A7: a terminal's auto index counts up in call order, so swapping calls swaps it."""
    from fransys_author import Design

    forward = Design(parts)
    x1 = forward.strip("X1")
    first = x1.terminal("TEST-TB")
    second = x1.terminal("TEST-TB")
    assert (first.key[-1], second.key[-1]) == ("1", "2")

    # explicit indexes reproduce a chosen key regardless of call order (A7)
    explicit = Design(parts)
    strip = explicit.strip("X1")
    later = strip.terminal("TEST-TB", index=2)
    earlier = strip.terminal("TEST-TB", index=1)
    assert earlier.key[-1] == "1"
    assert later.key[-1] == "2"
    assert earlier.id == first.id
    assert later.id == second.id
