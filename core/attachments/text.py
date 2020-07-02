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
    """
    Base text tree node
    """


class TextGroup(TextNode):
    """
    Group of nodes with common style or attributes
    """
    children: Tuple[TextNode, ...]


class TextContent(TextNode):
    """
    Terminal node with actual text content
    """
    text: str


class Mention(TextContent):
    """
    Mention of a user
    """
    user: User


class CodeBlock(TextContent):
    """
    Multiline code block with optional syntax highlighting
    """
    language: Optional[str]


class ListType(str, Enum):
    """
    List type: ordered or unordered
    """
    OL = ORDERED = 'OL'
    UL = UNORDERED = 'UL'


class TextList(TextGroup):
    """
    Ordered or unordered list
    """
    type: ListType


class TextLink(TextGroup):
    """
    Text link - region of text associated with a URL
    """
    url: AnyUrl


class Colored(TextGroup):
    """
    Colored text
    """
    color: Color


class Bold(TextGroup):
    """
    Bold text
    """


class Italic(TextGroup):
    """
    Italic text
    """


class Strike(TextGroup):
    """
    Strikethrough text
    """


class Underline(TextGroup):
    """
    Underlined text
    """


class InlineCode(TextGroup):
    """
    Inline monospace (code) block
    """


# Update class reference Text -> TextNode
Text.update_forward_refs()
