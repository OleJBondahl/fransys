"""Step times of a build and a write (decision 0198): the facade times calls from outside.

CPU time is `time.process_time()`, wall time `time.perf_counter()`; outputs read no clock.
"""

import dataclasses
import json
import time
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from collections.abc import Callable

TIMES_FILE = "build-times.json"


@dataclasses.dataclass(frozen=True, slots=True)
class StepTime:
    """One step's name and its CPU and wall seconds."""

    step: str
    cpu: float
    wall: float


@dataclasses.dataclass(frozen=True, slots=True)
class BuildTimes:
    """The timed steps in the order they ran; `str` is one line per step."""

    steps: tuple[StepTime, ...] = ()

    @override
    def __str__(self) -> str:
        total = sum(s.cpu for s in self.steps)
        width = max((len(s.step) for s in self.steps), default=0)
        return "\n".join(
            f"{s.step:<{width}}  {s.cpu:8.3f} cpu s  {s.wall:8.3f} wall s  "
            f"{(100 * s.cpu / total if total else 0.0):5.1f}% of cpu"
            for s in self.steps
        )

    def as_json(self) -> str:
        rows = [{"step": s.step, "cpu_s": s.cpu, "wall_s": s.wall} for s in self.steps]
        return json.dumps({"steps": rows}, indent=2) + "\n"


class Timer:
    """Runs calls and keeps their times, after any `steps` already taken."""

    def __init__(self, steps: tuple[StepTime, ...] = ()) -> None:
        self._steps = list(steps)

    def run[**P, R](self, step: str, call: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        cpu, wall = time.process_time(), time.perf_counter()
        made = call(*args, **kwargs)
        self._steps.append(StepTime(step, time.process_time() - cpu, time.perf_counter() - wall))
        return made

    def times(self) -> BuildTimes:
        return BuildTimes(tuple(self._steps))
