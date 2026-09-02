import abc
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Status(Enum):
    """Possible health states of a component (ok < degraded < down)."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"

    def __lt__(self, other):
        if not isinstance(other, Status):
            return NotImplemented

        order = {Status.OK: 0, Status.DEGRADED: 1, Status.DOWN: 2}

        return order[self] < order[other]


@dataclass(frozen=True)
class ComponentResult:
    """Data container for health status of a single component."""

    name: str
    status: Status
    last_check: datetime
    details: Any = None

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "details": self.details,
        }


class BaseChecker(abc.ABC):
    """Abstract base class for checkers."""

    @abc.abstractmethod
    def check(self) -> ComponentResult:
        ...
