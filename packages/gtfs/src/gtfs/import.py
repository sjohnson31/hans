import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass

from aiocsv import AsyncReader
import aiohttp
import aiosqlite
from stream_unzip import async_stream_unzip


@dataclass
class CacheId:
    etag: str
    last_modified_date: str


async def import_gtfs_db(
    db: aiosqlite.Connection,
    zip_download_url: str,
    session: aiohttp.ClientSession,
    cache_id: CacheId | None = None,
    loop: asyncio.AbstractEventLoop = None,
) -> CacheId:
    if not loop:
        loop = asyncio.get_event_loop()

    if cache_id:
        headers = {
            'If-None-Match': cache_id.etag,
            'If-Modified-Since': cache_id.last_modified_date,
        }
    else:
        headers = None

    async with (
        session.get(zip_download_url, headers=headers) as resp,
    ):
        cache_id = CacheId(
            etag=resp.headers['ETag'],
            last_modified_date=resp.headers.get('Last-Modified'),
        )
        if resp.status == 304:
            return cache_id
        elif resp.status != 200:
            raise RuntimeError(f'Unexpected response code: {resp.status}')

        async for file_name, _, unzipped_chunks in async_stream_unzip(
            resp.content.iter_any()
        ):
            if file_name == b'routes.txt':
                async for row in readCSVWithHeader(
                    AsyncReader(ByteStreamReader(unzipped_chunks))
                ):
                    print(row)
            else:
                async for _ in unzipped_chunks:
                    pass

        return cache_id


async def aenumerate(things):
    i = 0
    async for thing in things:
        yield i, thing


async def readCSVWithHeader(reader: AsyncReader) -> AsyncIterator[dict[str, str], None]:
    iter = aiter(reader)
    async for rowIdx, row in aenumerate(iter):
        if rowIdx == 0:
            rowNameByIdx = row
            continue

        namedRow = {}
        for colIdx, col in enumerate(row):
            namedRow[rowNameByIdx[colIdx]] = col

        yield namedRow


class ByteStreamReader:
    def __init__(self, bytestream: AsyncGenerator[bytes, None], encoding='utf8'):
        self.bytestream = aiter(bytestream)
        self.encoding = encoding
        self.leftover_bytes = bytearray()

    async def read(self, size: int) -> bytes:
        try:
            while len(self.leftover_bytes) < size:
                chunk = await anext(self.bytestream)
                self.leftover_bytes.extend(chunk)

            to_return = self.leftover_bytes[:size]
            self.leftover_bytes = self.leftover_bytes[size:]
        except StopAsyncIteration:
            to_return = self.leftover_bytes
            self.leftover_bytes = bytearray()

        return str(to_return, self.encoding)


async def main():
    async with aiohttp.ClientSession() as session, aiosqlite.connect('./test.db') as db:
        cache_id = await import_gtfs_db(
            db=db,
            zip_download_url='https://data.trilliumtransit.com/gtfs/sfbayferry-ca-us/sfbayferry-ca-us.zip',
            session=session,
            # cache_id=CacheId(
            #     '"e72a-6324d38a08350"',
            #     last_modified_date='Wed, 09 Apr 2025 00:05:04 GMT',
            # ),
        )
        print(cache_id)


if __name__ == '__main__':
    asyncio.run(main())
