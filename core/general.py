from typing import Tuple, Callable, Any, Optional
from pydantic import BaseModel, Field, Extra
from datetime import datetime
from uuid import uuid4
import asyncio


class Type(BaseModel):
    """
    Base for all core types - immutable pydantic dataclass (model)
    """
    id: str = Field(default_factory=lambda: str(uuid4()))  # TODO: DRAFT

    class Config:
        allow_mutation = False
        extra = Extra.ignore

    def __setattr__(self, key, value):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            super().__setattr__(key, value)


class Provider(Type):  # TODO: DRAFT
    def __init__(self, **data):
        super().__init__(**data)
        self._subscribers = set()

    async def setup(self):
        raise NotImplementedError

    def subscribe(self, callback: Callable):
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable):
        self._subscribers.remove(callback)

    def notify(self, data: Any):
        tasks = [coro(data) for coro in self._subscribers]
        for task in tasks: asyncio.ensure_future(task)


class User(Type):
    """
    User of a messenger (may be a bot)
    """
    is_bot: bool
    username: Optional[str]
    full_name: str
    short_name: str


class Chat(Type):
    """
    Chat / group / channel
    """


class Attachment(Type):
    """
    Base class for all attachments
    """


class Message(Type):
    """
    Core message type - basically, just a list of attachments + some metadata
    """
    when: datetime
    sender: User
    chat: Chat
    content: Tuple[Attachment, ...]
