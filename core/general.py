from core import Type
from datetime import datetime
from typing import Tuple


class User(Type):
    """
    User of a messenger (may be a bot)
    """


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
    time: datetime
    sender: User
    chat: Chat
    content: Tuple[Attachment, ...]
