import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pychromecast import Chromecast, get_chromecasts
from pychromecast.controllers.receiver import CastStatus, CastStatusListener
import uvicorn


class ScreenStatusListener(CastStatusListener):
    def new_cast_status(self, status: CastStatus) -> None:
        print(f'{status=}\n')


@asynccontextmanager
async def lifespan(app: FastAPI):
    status_listener = ScreenStatusListener()

    def callback(chromecast: Chromecast):
        print(f'{chromecast=}\n')
        chromecast.register_status_listener(status_listener)
        chromecast.wait()

    browser = get_chromecasts(blocking=False, callback=callback)
    yield
    browser.stop_discovery()


app = FastAPI(lifespan=lifespan)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
