from bs4 import BeautifulSoup
from markdown import markdown
from core import Attachment
from html import escape


class Text(Attachment):
    """
    Arbitrary tree-like text content
    """
    tree: BeautifulSoup

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def from_string(text: str) -> 'Text':
        return Text.from_html(f'<body>{escape(text)}</body>')

    @staticmethod
    def from_markdown(md: str) -> 'Text':
        return Text.from_html(markdown(md))

    @staticmethod
    def from_html(html: str):
        return Text(tree=BeautifulSoup(html, 'lxml'))
