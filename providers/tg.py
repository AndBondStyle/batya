from aiohttp import ClientSession
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
            pass
        return content


class TgText(Text):
    @staticmethod
    def from_entities(text: str, entities: list):
        for x in entities:
            x['end'] = x['offset'] + x['length']

    @staticmethod
    def wrap(root, start, end, tag):
        pass
