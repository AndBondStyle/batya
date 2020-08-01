from core import Attachment, Message
from typing import Tuple, Optional
from pydantic import AnyHttpUrl
from enum import Enum


class Forward(Attachment):
    """
    Group of forwarded messages
    """
    messages: Tuple[Message, ...] = ()


class DocumentType(str, Enum):
    UNKNOWN = 'UNKNOWN'
    IMAGE = 'IMAGE'
    AUDIO = 'AUDIO'
    VIDEO = 'VIDEO'
    GIF = 'GIF'


class Document(Attachment):
    """
    File attachment
    """
    type: DocumentType = DocumentType.UNKNOWN
    filename: Optional[str]
    caption: Optional[str]
    url: Optional[AnyHttpUrl]
    size: int = -1
    do_not_process: bool = False

    async def download(self, offset: int = 0, limit: int = -1) -> bytes:
        """
        Download file contents
        :param offset: offset from the start
        :param limit: size of chunk to download, -1 for unlimited size
        :return: bytes of requested chunk
        """
        raise NotImplementedError
