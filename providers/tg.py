from aiohttp import ClientSession
from bs4 import BeautifulSoup
from core.attachments import *
from core import *
import asyncio


class Telegram(Provider):
    id = 'telegram'
    token: str

    def __init__(self, **data):
        super().__init__(**data)
        self._http = ClientSession()

    async def request(self, method, data=None):
        url = f'https://api.telegram.org/bot{self.token}/{method}'
        res = await self._http.post(url, json=data or {})
        data = await res.json()
        return data.get('result')

    async def setup(self):
        data = await self.request('getMe')
        assert data is not None, 'API Authentication Failed'
        asyncio.ensure_future(self.polling_loop())

    async def polling_loop(self):
        loop = asyncio.get_event_loop()
        offset = 0
        async with self._http:
            while loop.is_running():
                data = await self.request('getUpdates', {'offset': offset})
                offset = max((x['update_id'] for x in data), default=0) + 1
                for update in data:
                    # self.notify(update)
                    if 'message' in update:
                        message = TgMessage.from_json(update['message'])
                        self.notify(message)


class TgUser(User):
    @staticmethod
    def from_json(data) -> 'TgUser':
        return TgUser(
            id=data['id'],
            is_bot=data['is_bot'],
            short_name=data['first_name'],
            full_name=(data['first_name'] + ' ' + data.get('last_name', '')).strip(),
            language=data.get('language_code'),
        )

    @staticmethod
    def from_username(username: str) -> 'TgUser':
        # TODO (SPOILER: VERY HARD)
        pass


class TgChat(Chat):
    @staticmethod
    def from_json(data) -> 'TgChat':
        return TgChat(
            id=data['id'],
            type=ChatType.USER if data['type'] == 'private' else ChatType.GROUP,
        )


class TgMessage(Message):
    @staticmethod
    def from_json(data) -> 'TgMessage':
        return TgMessage(
            id=data['message_id'],
            when=data['date'],
            sender=TgUser.from_json(data['from']),
            chat=TgChat.from_json(data['chat']),
            content=TgMessage.parse_content(data),
        )

    @staticmethod
    def parse_content(data):
        content = []
        if data.get('text'):
            content.append(TgText.from_json(data))
        return tuple(content)


class TgText(Text):
    @staticmethod
    def from_json(data) -> 'TgText':
        parser = TgTextParser(data['text'], data.get('entities', []))
        return parser.parse()


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

    def __init__(self, text: str, entities: list):
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
        return TgText(tree=self.soup)
