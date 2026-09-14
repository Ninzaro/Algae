from abc import ABC, abstractmethod
from typing import Any

from alphaforge.models.domain import Signal, StrategyContext
from alphaforge.models.enums import Timeframe


class Strategy(ABC):
    """Pure strategy contract. Implementations must not import brokers or risk."""

    id: str
    name: str
    description: str = ""
    symbols: list[str]
    timeframe: Timeframe = Timeframe.D1
    params: dict[str, Any]

    def with_params(self, params: dict[str, Any]) -> "Strategy":
        """Return a new instance with updated parameters. Override in subclasses."""
        raise NotImplementedError

    @abstractmethod
    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        """Return zero or more signals from the supplied read-only context."""
