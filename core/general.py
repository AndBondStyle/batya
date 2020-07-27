from typing import Tuple, Callable, Any, Optional
from pydantic import BaseModel, Field, Extra
from datetime import datetime
from uuid import uuid4
from enum import Enum
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
        for coro in self._subscribers:
            asyncio.ensure_future(coro(data))


class User(Type):
    """
    User of a messenger (may be a bot)
    """
    is_bot: bool
    full_name: str
    short_name: str
    language: Optional[str]


class ChatType(str, Enum):
    USER = 'USER'
    GROUP = 'GROUP'


class Chat(Type):
    """
    Chat / group / channel
    """
    type: ChatType

    @property
    def is_user(self) -> bool:
        return self.type == ChatType.USER

    @property
    def is_group(self) -> bool:
        return self.type == ChatType.GROUP


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
