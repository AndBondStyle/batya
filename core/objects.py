from core import Type
from datetime import datetime
from typing import Tuple


class User(Type):
    """
    TODO: TBD IN DOCS
    """
    pass


class Attachment(Type):
    """
    Base class for all attachments
    """


class Message(Type):
    """
    Core message type - basically, just a list of attachments + some metadata.
    """
    sent_by: User  # TODO: TBD IN DOCS
    sent_at: datetime  # TODO: TBD IN DOCS
    origin: str  # TODO: TBD IN DOCS
    content: Tuple[Attachment, ...]
