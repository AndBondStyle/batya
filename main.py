from networks.tg import Telegram
import asyncio


async def callback(message):
    print('>>>', message.content)


tg = Telegram(token='')
tg.subscribe(callback)
loop = asyncio.get_event_loop()
loop.create_task(tg.setup())
loop.run_forever()
