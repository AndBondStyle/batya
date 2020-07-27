from core import Attachment
from lxml import etree


class Text(Attachment):
    """
    Arbitrary tree-like text content
    """
    tree: etree.ElementTree
