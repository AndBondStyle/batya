from collections import defaultdict, namedtuple
from types import FunctionType
from typing import *
import warnings
import asyncio
import re

# Unique object to mark missing values
MISSING = type('MISSING', (), {'__repr__': lambda x: 'MISSING'})()
# Types not considered to be converted into fields
UNTOUCHED_TYPES = FunctionType, property, type, classmethod, staticmethod
# Field descriptor type
Field = namedtuple('Field', ['type', 'default', 'fetchers'])
# Fetcher descriptor type
Fetcher = namedtuple('Fetcher', ['name', 'fetches', 'requires'])


# Convenience function to bypass getattr hooks
def do_getattr(self: Any, name: str) -> Any:
    return object.__getattribute__(self, name)


# Convenience function to bypass setattr hooks
def do_setattr(self: Any, name: str, value: Any) -> None:
    object.__setattr__(self, name, value)


# Helper function to filter field candidates
def is_valid_field(name: str, value: Any = MISSING) -> bool:
    if (
            not name  # Empty identifier (?)
            or name.startswith('__')  # Probably something magic
            or name[0].isupper()  # Regular constant
            or re.match(r'^_[A-Z]', name)  # Private constant (i.e. _CONST)
    ):
        # -> not valid identifier
        return False
    if value is not MISSING and isinstance(value, UNTOUCHED_TYPES):
        # -> doesn't look like a field
        return False
    return True


class MetaModel(type):
    def __new__(mcs, name, bases, attrs):
        # Collect parent fields
        fields: Dict[str, Field] = {}
        for parent in bases[::-1]:  # TODO: ?
            fields.update(parent.__fields__)
        # Process @fetches-decorated methods
        fetchers = defaultdict(list)
        for name, field in fields.items():
            fetchers[name].extend(field.fetchers)
        for name, value in attrs.items():
            if hasattr(value, '__fetches__'):
                for field_name in value.__fetches__:
                    fetcher = Fetcher(
                        name=name,
                        fetches=value.__fetches__,
                        requires=value.__requires__,
                    )
                    fetchers[field_name].append(fetcher)
        # Process class fields
        annotations = attrs.get('__annotations__', {})
        for name, type in annotations.items():
            value = attrs.get(name, MISSING)
            if is_valid_field(name, value):
                fields[name] = Field(
                    type=type,
                    default=value,
                    fetchers=tuple(fetchers.get(name, []))
                )
        # Update fields if new fetchers are found
        for name, field in fields.items():
            if len(field.fetchers) != len(fetchers.get(name, [])):
                fields[name] = Field(
                    type=field.type,
                    default=field.default,
                    fetchers=tuple(fetchers.get(name, [])),
                )
        # Inject class vars
        attrs['__fields__'] = fields
        attrs['__fetchers__'] = fetchers
        return super().__new__(mcs, name, bases, attrs)


class Model(metaclass=MetaModel):
    if TYPE_CHECKING:
        # Populated by MetaModel, defined for type checking only
        __fields__: Dict[str, Field] = {}
        __fetchers__: Dict[str, Iterable[Fetcher]] = {}
        __fetched__: Set[str] = {}

    def __init__(self, **kwargs):
        # Field set keeping track of what fields was requested by .fetch(...)
        do_setattr(self, '__fetched__', set())
        # Populate fields with either MISSING or value from kwargs
        for key in do_getattr(self, '__fields__'):
            value = kwargs.pop(key, MISSING)
            if value is not MISSING:
                # TODO: TYPE CHECK, COERCION, NESTED OBJECTS
                ...
            do_setattr(self, key, value)
        if kwargs:
            # Crash if unknown fields were passed in kwargs
            raise AttributeError(f'Unexpected fields: {" ".join(kwargs.keys())}')

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if item in do_getattr(self, '__fields__'):
            # One of statically-declared fields
            if value == MISSING:
                # TODO: DUMB MODE: FETCH AUTOMATICALLY
                raise AttributeError(
                    f'Missing value for field \'{item}\'. '
                    f'Did you forget to call .fetch(...)?'
                )
            if value not in do_getattr(self, '__fetched__'):
                warnings.warn(
                    f'Field \'{item}\' luckily has a value, but wasn\'t properly'
                    f' requested. Did you forget to call .fetch(...)?',
                    stacklevel=2
                )
        # Magic, dynamic or unknown field
        return value

    async def fetch(self, *fields):
        pass  # TODO: ???


# Decorator to mark field-fetching methods and their dependencies
def fetches(*fields, requires=()):
    def wrap(func):
        if not asyncio.iscoroutinefunction(func):
            raise ValueError('Use @fetches decorator on async methods only')
        do_setattr(func, '__fetches__', tuple(fields))
        do_setattr(func, '__requires__', tuple(requires))
        return func

    return wrap


# ==== SAMPLE SECTION BELOW THIS POINT ====


class Base(Model):
    id: int


class User(Base):
    locale: Optional[str]
    is_bot: bool
    short_name: str
    full_name: str
    username: str
    avatar: Optional[bytes]
    profile: Optional[str]


class UserImpl(User):
    _first_name: str
    _last_name: str

    @fetches('id', requires=['username'])
    async def fetch_id_by_username(self):
        print('fetching id')
        # ... API request ...
        self.id = 123

    @fetches('_first_name', '_last_name', requires=['id'])
    async def fetch_raw_names(self):
        print('fetching raw names')
        # ... API request ...
        self._first_name = 'James'
        self._last_name = 'Bond'

    @fetches('short_name', 'full_name', requires=['_first_name', '_last_name'])
    async def fetch_proper_names(self):
        print('fetching proper names')
        self.short_name = self._first_name
        self.full_name = f'{self._first_name} {self._last_name}'.strip()


async def main():
    user = UserImpl(username='test')
    print('fields:', user.__fields__)
    print('fetchers:', user.__fetchers__)
    await user.fetch('short_name')
    print('Short name is:', user.short_name)
    print('Full name is:', user.full_name)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
