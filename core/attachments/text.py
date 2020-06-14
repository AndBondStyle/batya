from core import Attachment, User, Type
from typing import Tuple, Optional
from pydantic import AnyUrl
from pydantic.color import Color
from enum import Enum


class Text(Attachment):
    """
    Arbitrary tree-like text content
    """
    root: 'TextNode'


class TextNode(Type):
    pass


class TextGroup(TextNode):
    children: Tuple[TextNode, ...]


class TextContent(TextNode):
    text: str


class Mention(TextContent):
    user: User


class CodeBlock(TextContent):
    language: Optional[str]


class ListType(str, Enum):
    OL = ORDERED = 'OL'
    UL = UNORDERED = 'UL'


class TextList(TextGroup):
    type: ListType


class TextLink(TextGroup):
    url: AnyUrl


class Colored(TextGroup):
    color: Color


class Bold(TextGroup): pass
class Italic(TextGroup): pass
class Strike(TextGroup): pass
class Underline(TextGroup): pass
class InlineCode(TextGroup): pass
