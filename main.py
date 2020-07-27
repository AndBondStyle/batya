from providers.tg import Telegram
import asyncio


async def callback(data):
    print(data)


tg = Telegram(token='')
tg.subscribe(callback)
loop = asyncio.get_event_loop()
loop.create_task(tg.setup())
loop.run_forever()
