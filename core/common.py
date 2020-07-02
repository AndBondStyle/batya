from pydantic import BaseModel


class Type(BaseModel):
    """
    Base for all core types - immutable pydantic dataclass (model)
    """

    class Config:
        allow_mutation = False
