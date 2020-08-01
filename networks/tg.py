from core.attachments.general import Forward
from core.attachments import *
from core import *

from async_property import async_property
from collections import defaultdict
from aiohttp import ClientSession
from typing import Optional, List
from bs4 import BeautifulSoup
import warnings
import asyncio


class Telegram(Network):
    id = 'telegram'
    token: str

    def __init__(self, **data):
        super().__init__(**data)
        self.http = ClientSession()
        self.pid = ID(native_id=None, origin=self)

    def notify(self, data):
        for coro in self._subscribers:
            asyncio.ensure_future(coro(data))

    async def request(self, method, data=None):
        url = f'https://api.telegram.org/bot{self.token}/{method}'
        res = await self.http.post(url, json=data or {})
        data = await res.json()
        return data.get('result')

    async def setup(self):
        data = await self.request('getMe')
        assert data is not None, 'API Authentication Failed'
        asyncio.ensure_future(self.polling_loop())

    async def polling_loop(self):
        loop = asyncio.get_event_loop()
        offset = 0
        async with self.http:
            while loop.is_running():
                data = await self.request('getUpdates', {'offset': offset})
                if not data: continue
                offset = max((x['update_id'] for x in data)) + 1
                groups = self.groupify_updates(data)
                if 'message' in groups: self.process_messages(groups.pop('message'))
                if groups: warnings.warn(f'[!] Unsupported updates: {groups.keys()}')

    def groupify_updates(self, updates):
        groups = defaultdict(list)
        for update in updates:
            update.pop('update_id')
            kind = next(iter(update.keys()))
            groups[kind].append(update)
        return groups

    def process_messages(self, updates):
        groups = defaultdict(list)
        for update in updates:
            message = TgMessage.from_json(self.pid, update['message'])
            groups[message.chat.id.native_id].append(message)
        for group in groups.values():
            self.process_message_group(group)

    def process_message_group(self, group: List['TgMessage']):
        prev_message = group[0]
        forward_holder = None
        forward_attachment = None
        for message in group[1:] + [None]:
            if self.can_merge_strict(prev_message, message):
                prev_message = self.merge(prev_message, message)
            elif forward_holder is not None:
                forward_attachment = forward_attachment.copy(update={
                    'messages': list(forward_attachment.messages) + [prev_message],
                })
                if not self.can_merge(forward_holder, message):
                    forward_holder = forward_holder.copy(update={
                        'content': list(forward_holder.content) + [forward_attachment],
                    })
                    self.notify(forward_holder)
                    forward_holder = None
                    forward_attachment = None
                prev_message = message
            elif self.is_forward(message) and self.can_merge(prev_message, message):
                if self.is_forward(prev_message):
                    forward_holder = TgMessage.from_json(
                        self.pid, prev_message.id.native_obj, parse_forward=False
                    ).copy(update={'content': []})
                else:
                    forward_holder = prev_message
                forward_attachment = Forward(id=self.pid.clone())
                prev_message = message
            else:
                self.notify(prev_message)
                prev_message = message

    def is_forward(self, message):
        if message is None: return False
        return 'forward_date' in message.id.native_obj

    def can_merge_strict(self, a, b) -> bool:
        if a is None or b is None: return False
        if a.when != b.when: return False
        if a.sender.id != b.sender.id: return False
        mgid_a = a.id.native_obj.get('media_group_id', 0)
        mgid_b = b.id.native_obj.get('media_group_id', 1)
        if mgid_a == mgid_b: return True
        return False

    def can_merge(self, a, b) -> bool:
        if a is None or b is None: return False
        when_a = a.id.native_obj['date']
        when_b = b.id.native_obj['date']
        if when_a != when_b: return False
        uid_a = a.id.native_obj['from']['id']
        uid_b = b.id.native_obj['from']['id']
        if uid_a != uid_b: return False
        if self.is_forward(b): return True
        warnings.warn(f'[!] Merge check confusion:\n{a}\n{b}')
        return False

    def merge(self, a: 'TgMessage', b: 'TgMessage') -> 'TgMessage':
        return TgMessage(
            id=b.id,
            when=b.when,
            sender=b.sender,
            chat=b.chat,
            content=a.content + b.content,
        )


# TODO: LAZY ENRICHMENT
class TgUser(User):
    _first_name: Optional[str]
    _last_name: Optional[str]
    _username: Optional[str]

    @classmethod
    def from_json(cls, pid, data):
        if data is None: return None
        return TgUser(
            id=pid.clone(data['id'], data),
            is_bot=data['is_bot'],
            _first_name=data.get('first_name'),
            _last_name=data.get('last_name'),
            _username=data.get('username'),
            # locale=data.get('language_code'),
            locale=None,  # TODO LATER
        )

    @async_property
    async def short_name(self):
        if self._first_name is None: raise RuntimeError
        return self._first_name

    @async_property
    async def full_name(self):
        return f'{await self.short_name} {self._last_name or ""}'.strip()

    @async_property
    async def username(self):
        return self._username

    @async_property
    async def avatar(self):
        pass  # TODO

    @async_property
    async def profile(self):
        return f'https://t.me/{await self.username}'

    @staticmethod
    def from_username(username: str) -> 'TgUser':
        pass  # TODO (SPOILER: VERY HARD)


class TgChat(Chat):
    @classmethod
    def from_json(cls, pid, data):
        return TgChat(
            id=pid.clone(data['id'], data),
            type=ChatType.USER if data['type'] == 'private' else ChatType.GROUP,
        )


class TgMessage(Message):
    @classmethod
    def from_json(cls, pid, data, parse_forward=True):
        data_copy = data.copy()
        if parse_forward and 'forward_date' in data:
            data['date'] = data['forward_date']
            data['from'] = data.get('forward_from')
            data['chat'] = data.get('forward_from_chat', data['chat'])
            data['message_id'] = data.get('forward_from_message_id', data['message_id'])
            # TODO: MORE RESEARCH
        return TgMessage(
            id=pid.clone(data['message_id'], data_copy),
            when=data['date'],
            sender=TgUser.from_json(pid, data['from']),
            chat=TgChat.from_json(pid, data['chat']),
            content=TgMessage.parse_content(pid, data),
        )

    @staticmethod
    def parse_content(pid: ID, data: dict):
        content = []
        if 'text' in data: content.append(TgText.from_json(pid, data))
        elif 'caption' in data: content.append(TgText.from_string(pid, data['caption']))
        return tuple(content)


class TgText(Text):
    @classmethod
    def from_json(cls, pid, data):
        return TgTextParser(pid, data['text'], data.get('entities', [])).parse()


class TgTextParser:
    SIMPLE_TAGS = {
        'bold': 'b',
        'italic': 'i',
        'underline': 'u',
        'strikethrough': 's',
        'code': 'code',
    }
    CURRENTLY_UNSUPPORTED = (
        'hashtag',
        'cashtag',
        'bot_command',
        'email',
        'phone_number',
    )

    def __init__(self, pid: ID, text: str, entities: list):
        self.pid = pid
        self.text = text
        self.soup = BeautifulSoup('<root></root>', 'lxml')
        self.entities = []
        for x in entities:
            e = x.copy()
            e['children'] = []
            e['range'] = range(x['offset'], x['offset'] + x['length'])
            self.entities.append(e)

    def is_inside(self, outer: range, inner: range):
        return outer.start <= inner.start and outer.stop >= inner.stop

    def treeify(self, entities: list, candidate: dict):
        for i, x in enumerate(entities):
            if self.is_inside(x['range'], candidate['range']):
                self.treeify(x['children'], candidate)
                break
        else:
            entities.append(candidate)
            entities.sort(key=lambda e: e['offset'])

    def tag_for_entity(self, entity: dict):
        kind = entity['type']
        if kind == 'root':
            tag = self.soup.new_tag('root')
        elif kind in self.SIMPLE_TAGS:
            tag = self.soup.new_tag(self.SIMPLE_TAGS[kind])
        elif kind == 'mention':
            tag = self.soup.new_tag('m')
            tag.attrs['user'] = '???'
        elif kind == 'url':
            tag = self.soup.new_tag('a')
            tag.attrs['href'] = '???'
        elif kind == 'pre':
            tag = self.soup.new_tag('pre')
            tag.lang = entity['language']
        elif kind == 'text_link':
            tag = self.soup.new_tag('a')
            tag.attrs['href'] = entity['url']
        elif kind == 'text_mention':
            tag = self.soup.new_tag('m')
            # TODO: GLOBAL ID?
            tag.attrs['user'] = entity['user']['id']
        else:
            tag = self.soup.new_tag('span')
            tag.attrs['class'] = 'unsupported'
            tag.attrs['kind'] = kind
            tag.attrs['origin'] = 'tg'
        return tag

    def postprocess(self, tag, entity):
        kind = entity['type']
        if kind == 'mention':
            # TODO: GLOBAL ID? USER FROM USERNAME?
            tag.attrs['user'] = tag.text
        elif kind == 'url':
            tag.attrs['href'] = tag.text

    def build(self, root: dict):
        tag = self.tag_for_entity(root)
        offset = root['offset']
        for x in root['children']:
            new_offset = x['offset']
            if new_offset > offset:
                text_slice = self.text[offset:new_offset]
                tag.append(self.soup.new_string(text_slice))
            tag.append(self.build(x))
            offset = new_offset + x['length']
        text_slice = self.text[offset:root['offset'] + root['length']]
        if text_slice: tag.append(self.soup.new_string(text_slice))
        self.postprocess(tag, root)
        return tag

    def parse(self) -> TgText:
        tree_entities = []
        for x in self.entities:
            self.treeify(tree_entities, x)
        root = {
            'type': 'root',
            'offset': 0,
            'length': len(self.text),
            'children': tree_entities,
        }
        self.soup.root.replace_with(self.build(root))
        self.soup.root.unwrap()
        return TgText(id=self.pid.clone(), tree=self.soup)
