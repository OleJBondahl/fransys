"""A helper module that hides all its frames from origin capture, as a module global."""

__tracebackhide__ = True


def build_group(d):
    return d.group("G1")
