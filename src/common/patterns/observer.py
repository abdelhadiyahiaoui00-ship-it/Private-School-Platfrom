import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

PROJECT_ACCEPTED = "project.accepted"
PROJECT_REJECTED = "project.rejected"
TEAM_VALIDATED = "team.validated"
PROJECT_ASSIGNED = "project.assigned"
DELIVERABLE_UPLOADED = "deliverable.uploaded"
FEEDBACK_SUBMITTED = "feedback.submitted"
AUTHORIZATION_APPROVED = "authorization.approved"
AUTHORIZATION_REJECTED = "authorization.rejected"
DEFENSE_SCHEDULED = "defense.scheduled"
GRADE_ENTERED = "grade.entered"
ACCOUNT_CREATED = "account.created"
CHAT_MESSAGE_SENT = "chat.message_sent"
DEADLINE_REMINDER = "deadline.reminder"


class EventBus:
    _instance: "EventBus | None" = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = defaultdict(list)
        return cls._instance

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def publish(self, event: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)

    async def publish_async(self, event: str, payload: dict[str, Any]) -> None:
        tasks = []
        for handler in self._handlers.get(event, []):
            result = handler(payload)
            if asyncio.iscoroutine(result):
                tasks.append(result)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def clear(self) -> None:
        self._handlers.clear()


event_bus = EventBus()
