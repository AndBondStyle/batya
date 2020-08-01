from pydantic import BaseModel, Extra, AnyHttpUrl as URL
from typing import Tuple, Callable, Any, Optional
from async_property import async_property
from datetime import datetime
from enum import Enum
import json


class Network(BaseModel):
    """
    Representation of a specific (social) network / messaging platform
    """
    id: str

    class Config:
        # TODO: PATCH PYDANTIC
        extra = Extra.allow

    def __init__(self, **data):
        super().__init__(**data)
        self._subscribers = set()

    async def send(self, message: 'Message'):
        raise NotImplementedError

    async def setup(self):
        pass

    def subscribe(self, callback: Callable):
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable):
        self._subscribers.remove(callback)


class ID(BaseModel):
    native_id: Optional[str]
    native_obj: Optional[Any]
    origin: Network

    def clone(self, new_id: Optional[Any] = None, src_obj: Optional[Any] = None):
        new_id = str(new_id) if new_id else None
        return ID(native_id=new_id, native_obj=src_obj, origin=self.origin)

    def encode(self) -> str:
        # TODO: TEMPORARY DRAFT
        return json.dumps({
            'network': self.origin.id,
            'native': self.native_id,
        })

    @classmethod
    def decode(cls, batya, string) -> 'ID':
        # TODO: TEMPORARY DRAFT
        data = json.loads(string)
        network = batya.get_network(data['network'])
        return ID(native_id=data['native'], origin=network)

    def __eq__(self, other):
        if not isinstance(other, ID): return self.native_id == str(other)
        return self.origin.id == other.origin.id and self.native_id == other.native_id


class Type(BaseModel):
    """
    Base for all core types - pydantic-powered dataclass
    """
    id: ID

    class Config:
        # TODO: PATCH PYDANTIC
        extra = Extra.allow
        arbitrary_types_allowed = True

    @classmethod
    def from_json(cls, pid: ID, data: dict) -> __qualname__:
        # FIXME: PyCharm hack: disable "must implement all abstract methods"
        # noinspection PyRedundantParentheses
        raise (NotImplementedError)

    @classmethod
    async def from_id(cls, id: ID) -> __qualname__:
        # FIXME: PyCharm hack: disable "must implement all abstract methods"
        # noinspection PyRedundantParentheses
        raise (NotImplementedError)


class Locale(BaseModel):
    # TODO: TBD IN DOCS
    raw: str


class User(Type):
    """
    User of a messenger (may be a bot)
    """
    locale: Optional[Locale]
    is_bot: bool

    @async_property
    async def short_name(self) -> str:
        raise NotImplementedError

    @async_property
    async def full_name(self) -> str:
        raise NotImplementedError

    @async_property
    async def avatar(self) -> Optional['Document']:
        raise NotImplementedError

    @async_property
    async def profile(self) -> Optional[URL]:
        raise NotImplementedError


class ChatType(str, Enum):
    USER = 'USER'
    GROUP = 'GROUP'


# TODO: TBD IN SPEC
class Chat(Type):
    """
    Chat / group / channel
    """
    type: ChatType


class Attachment(Type):
    """
    Base class for all attachments
    """


class Message(Type):
    """
    Core message type - basically, just a list of attachments + some metadata
    """
    sender: Optional[User]
    when: datetime
    last_edit: Optional[datetime]
    chat: Chat
    content: Tuple[Attachment, ...]
