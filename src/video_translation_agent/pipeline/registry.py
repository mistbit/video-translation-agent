from collections import OrderedDict
from collections.abc import Callable, Iterable

from video_translation_agent.domain.enums import StageName
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)

StageHandler = Callable[[StageExecutionContext], StageExecutionResult | None]


class StageRegistry:
    def __init__(self, stage_order: Iterable[StageName]):
        self._stage_order = tuple(stage_order)
        self._handlers: OrderedDict[StageName, StageHandler] = OrderedDict()

    @property
    def stage_order(self) -> tuple[StageName, ...]:
        return self._stage_order

    def register(self, stage: StageName, handler: StageHandler) -> None:
        self._handlers[stage] = handler

    def get(self, stage: StageName) -> StageHandler:
        if stage not in self._handlers:
            raise KeyError(f"No handler registered for stage '{stage.value}'")
        return self._handlers[stage]
