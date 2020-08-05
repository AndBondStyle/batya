from typing import Optional
from inspect import isfunction

MISSING = type('MISSING', (), {'__repr__': lambda x: 'MISSING'})()


class MetaModel(type):
    def __new__(mcs, name, bases, attrs):
        print(name, bases, attrs)
        # Prepare fields metadata, collected from parents
        fields = {}
        for parent in bases:
            fields.update(parent.__fields__)
        # Process annotations
        for key in attrs.get('__annotations__', []):
            value = attrs.get(key)
            if not key.startswith('_') and not isfunction(value):
                fields[key] = MISSING
        # Inject fields metadata into __fields__
        attrs['__fields__'] = fields
        return super().__new__(mcs, name, bases, attrs)


class Model(metaclass=MetaModel):
    def __init__(self, **kwargs):
        data = object.__getattribute__(self, '__fields__')
        object.__setattr__(self, '__data__', data)
        for key in data.keys() & kwargs.keys():
            # TODO: TYPE CHECK, COERCION, NESTED OBJECTS
            data[key] = kwargs.pop(key)
        for key, value in kwargs:
            object.__setattr__(self, key, value)

    def __getattribute__(self, item):
        data = object.__getattribute__(self, '__data__')
        if item in data:
            value = data[item]
            if value == MISSING:
                # TODO: DUMB MODE: FETCH AUTOMATICALLY
                raise AttributeError(
                    f'Missing value for attribute \'{item}\'. '
                    f'Did you forget to call .fetch(...)?'
                )
            # TODO: WARN IF VALUE IS PRESENT, BUT WASN'T ACTUALLY FETCHED
            return value
        return super().__getattribute__(item)


class Base(Model):
    id: int


class User(Base):
    locale: Optional[str]
    is_bot: bool
    short_name: str
    full_name: str
    avatar: Optional[bytes]
    profile: Optional[str]


class UserImpl(User):
    _first_name: str
    _last_name: str


if __name__ == '__main__':
    t = UserImpl()
    print(t.id)
