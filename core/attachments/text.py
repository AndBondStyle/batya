from core import Attachment, ID
from bs4 import BeautifulSoup
from markdown import markdown
from html import escape


class Text(Attachment):
    """
    Arbitrary tree-like text content
    """
    tree: BeautifulSoup

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def from_string(pid: ID, text: str) -> 'Text':
        return Text.from_html(pid, f'<body>{escape(text)}</body>')

    @staticmethod
    def from_markdown(pid: ID, md: str) -> 'Text':
        return Text.from_html(pid, markdown(md))

    @staticmethod
    def from_html(pid: ID, html: str):
        return Text(id=pid.clone(), tree=BeautifulSoup(html, 'lxml'))
