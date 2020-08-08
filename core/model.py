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
# @fetches decorator metadata
FetcherDeco = namedtuple('FetcherDeco', ['fetches', 'not_fetches', 'requires'])
# Concise fetcher descriptor type
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
        # -> 'untouched' value type
        return False
    return True


class MetaModel(type):
    @staticmethod
    def extract_fields(bases, attrs) -> Dict[str, Field]:
        # Collect parent fields
        fields = {}
        for parent in bases[::-1]:
            if hasattr(parent, '__fields__'):
                fields.update(parent.__fields__)
        # Process class fields
        annotations = attrs.get('__annotations__', {})
        for name, type in annotations.items():
            value = attrs.get(name, MISSING)
            if is_valid_field(name, value):
                fields[name] = Field(
                    type=type,
                    default=value,
                    fetchers=(),
                )
        return fields

    @staticmethod
    def make_fetcher(name: str, deco: FetcherDeco, fields: Dict[str, Field]) -> Fetcher:
        fetches = set(deco.fetches)
        if '__all__' in fetches:
            fetches = set(fields)
        fetches -= set(deco.not_fetches)
        fetches -= set(deco.requires)
        diff = fetches - fields.keys()
        if diff:
            raise AttributeError(
                f'Unknown fields specified in @fetches decorator: {diff}. '
                f'Current model only has: {set(fields.keys())}'
            )
        return Fetcher(
            name=name,
            fetches=fetches,
            requires=deco.requires,
        )

    @staticmethod
    def extract_fetchers(attrs, fields: Dict[str, Field]) -> Dict[str, List[Fetcher]]:
        # Process @fetches-decorated methods
        fetchers = defaultdict(list)
        for name, field in fields.items():
            fetchers[name].extend(field.fetchers)
        for name, func in attrs.items():
            if hasattr(func, '__fetches__'):
                annotations = func.__fetches__
                for annotation in annotations:
                    fetcher = MetaModel.make_fetcher(name, annotation, fields)
                    for field_name in fetcher.fetches:
                        fetchers[field_name].append(fetcher)
        return fetchers

    def __new__(mcs, name, bases, attrs):
        fields = MetaModel.extract_fields(bases, attrs)
        fetchers = MetaModel.extract_fetchers(attrs, fields)
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
        for name, field in do_getattr(self, '__fields__').items():
            value = kwargs.pop(name, field.default)
            if value is not MISSING:
                # TODO: TYPE CHECK, COERCION, NESTED OBJECTS
                ...
            do_setattr(self, name, value)
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
def fetches(*fields, excluding=(), requires=()):
    def wrap(func):
        nonlocal fields, excluding
        if not asyncio.iscoroutinefunction(func):
            raise ValueError('Use @fetches decorator on async methods only')
        # Get or create list of annotations (FetchersDeco objects)
        annotations = list(getattr(func, '__fetches__', ()))
        # May be needed later for ellipsis-based shortcuts
        prev: Optional[FetcherDeco] = None if not annotations else annotations[-1]
        # Check arguments for ellipsis notation
        fields_with_ellipsis = ... in fields
        excluding_with_ellipsis = ... is excluding or ... in excluding
        if (fields_with_ellipsis or excluding_with_ellipsis) and prev is None:
            raise ValueError(
                'Can\'t resolve ellipsis notation. '
                'Is there any @fetches decorator below?'
            )
        if fields_with_ellipsis:
            fields = [x for x in fields if isinstance(x, str)]
            fields.extend(prev.fetches)
        if excluding_with_ellipsis:
            if excluding is not ...:
                excluding = [x for x in excluding if isinstance(x, str)]
                excluding.extend(prev.not_fetches)
            else:
                excluding = list(prev.not_fetches)
        # Accommodate for mixed-style requires
        # Example: requires = ('a', 'b', 'c', ('x, 'y'))
        #       common part -> ~~~~~~~~~~~~~   ~~~~~~~ <- variable part
        common_requires = [x for x in requires if isinstance(x, str)]
        variable_requires = [list(x) for x in requires if x not in common_requires]
        if not variable_requires: variable_requires.append([])
        # Generate & append new annotations
        for vr in variable_requires:
            new = FetcherDeco(
                fetches=tuple(fields),
                not_fetches=tuple(excluding),
                requires=tuple(common_requires + vr),
            )
            annotations.append(new)
        func.__fetches__ = tuple(annotations)
        return func

    return wrap


# ==== SAMPLE SECTION BELOW THIS POINT ====


class Base(Model):
    id: int


class User(Base):
    locale: Optional[str]
    is_bot: bool = False
    short_name: str
    full_name: str
    username: str
    avatar: Optional[bytes]
    profile: Optional[str]


class UserImpl(User):
    _first_name: str
    _last_name: str

    @fetches(..., excluding=..., requires=['username'])
    @fetches('__all__', excluding=('avatar', 'profile'), requires=['id'])
    async def test(self):
        pass

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
    from pprint import pprint
    user = UserImpl(username='test')
    print('Fields:')
    pprint(user.__fields__)
    print('Fetchers:')
    pprint(user.__fetchers__)

    print('Is bot:', user.is_bot)
    await user.fetch('short_name')
    print('Short name is:', user.short_name)
    print('Full name is:', user.full_name)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
