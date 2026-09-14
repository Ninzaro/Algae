from alphaforge.core.exceptions import NotFoundError, ValidationError
from alphaforge.core.logging import get_logger
from alphaforge.models.domain import Signal, StrategyContext, StrategyMeta
from alphaforge.strategies.base import Strategy

log = get_logger(__name__)


class StrategyRegistry:
    """In-process registry of pluggable, side-effect-free strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._enabled: dict[str, bool] = {}

    def register(self, strategy: Strategy, *, enabled: bool = True) -> None:
        """Register a strategy instance. Replaces any previous instance with the same id."""
        if not strategy.id:
            raise ValidationError("Strategy id must be non-empty")
        self._strategies[strategy.id] = strategy
        self._enabled[strategy.id] = enabled
        log.info("strategy.registered", strategy_id=strategy.id, enabled=enabled)

    def get(self, strategy_id: str) -> Strategy:
        strategy = self._strategies.get(strategy_id)
        if strategy is None:
            raise NotFoundError(f"Unknown strategy: {strategy_id}")
        return strategy

    def set_enabled(self, strategy_id: str, enabled: bool) -> Strategy:
        strategy = self.get(strategy_id)
        self._enabled[strategy_id] = enabled
        log.info("strategy.enabled", strategy_id=strategy_id, enabled=enabled)
        return strategy

    def is_enabled(self, strategy_id: str) -> bool:
        return self._enabled.get(strategy_id, False)

    def apply_enabled(self, flags: dict[str, bool]) -> None:
        """Apply persisted enabled flags for already-registered strategies."""
        for strategy_id, enabled in flags.items():
            if strategy_id in self._strategies:
                self._enabled[strategy_id] = enabled

    def list_meta(self) -> list[StrategyMeta]:
        return [
            StrategyMeta(
                id=s.id,
                name=s.name,
                description=s.description,
                enabled=self._enabled.get(s.id, False),
                symbols=list(s.symbols),
                timeframe=s.timeframe,
                params=dict(s.params),
            )
            for s in self._strategies.values()
        ]

    def generate_all(self, context: StrategyContext) -> list[Signal]:
        """Run every enabled strategy. Strategies must not mutate shared state."""
        signals: list[Signal] = []
        for strategy_id, strategy in self._strategies.items():
            if not self._enabled.get(strategy_id, False):
                continue
            produced = strategy.generate_signals(context)
            signals.extend(produced)
        return signals
