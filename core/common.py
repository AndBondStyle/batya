from pydantic import BaseModel


class Type(BaseModel):
    class Config:
        allow_mutation = False
