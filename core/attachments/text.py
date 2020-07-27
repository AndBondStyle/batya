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
        return Text.from_html(escape(text))

    @staticmethod
    def from_markdown(md: str) -> 'Text':
        return Text.from_html(markdown(md))

    @staticmethod
    def from_html(html: str):
        tree = BeautifulSoup(html, 'lxml')
        body = tree.find('body')
        if body: body.unwrap()
        html = tree.find('html')
        if html: html.unwrap()
        p = tree.find('p', recursive=False)
        if p: p.unwrap()
        return Text(tree=tree)

    def copy(self, **kwargs):
        if not kwargs.get('update', {}).get('tree'):
            kwargs.setdefault('update', {})['tree'] = self.tree.__copy__()
        return super().copy(**kwargs)
