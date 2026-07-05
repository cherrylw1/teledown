import asyncio
import logging
import math
from typing import Optional, List, AsyncGenerator, Union, Awaitable

from telethon import utils, TelegramClient
from telethon.crypto import AuthKey
from telethon.network import MTProtoSender
from telethon.tl.alltlobjects import LAYER
from telethon.tl.functions import InvokeWithLayerRequest
from telethon.tl.functions.auth import ExportAuthorizationRequest, ImportAuthorizationRequest
from telethon.tl.functions.upload import GetFileRequest
from telethon.tl.types import (Document, InputFileLocation, InputDocumentFileLocation,
                               InputPhotoFileLocation, InputPeerPhotoFileLocation)

log: logging.Logger = logging.getLogger("telethon")

TypeLocation = Union[Document, InputDocumentFileLocation, InputPeerPhotoFileLocation,
                     InputFileLocation, InputPhotoFileLocation]

class DownloadSender:
    client: TelegramClient
    sender: MTProtoSender
    request: GetFileRequest
    remaining: int
    stride: int

    def __init__(self, client: TelegramClient, sender: MTProtoSender, file: TypeLocation, offset: int, limit: int,
                 stride: int, count: int) -> None:
        self.sender = sender
        self.client = client
        self.request = GetFileRequest(file, offset=offset, limit=limit)
        self.stride = stride
        self.remaining = count

    async def next(self) -> Optional[bytes]:
        if not self.remaining:
            return None
        result = await self.client._call(self.sender, self.request)
        self.remaining -= 1
        self.request.offset += self.stride
        return result.bytes

    def disconnect(self) -> Awaitable[None]:
        return self.sender.disconnect()

class ParallelTransferrer:
    client: TelegramClient
    loop: asyncio.AbstractEventLoop
    dc_id: int
    senders: Optional[List[DownloadSender]]
    auth_key: AuthKey

    def __init__(self, client: TelegramClient, dc_id: Optional[int] = None) -> None:
        self.client = client
        self.loop = self.client.loop
        self.dc_id = dc_id or self.client.session.dc_id
        self.auth_key = (None if dc_id and self.client.session.dc_id != dc_id
                         else self.client.session.auth_key)
        self.senders = None

    async def _cleanup(self) -> None:
        if self.senders:
            await asyncio.gather(*[sender.disconnect() for sender in self.senders])
            self.senders = None

    @staticmethod
    def _get_connection_count(file_size: int, max_count: int = 12,
                               full_size: int = 100 * 1024 * 1024) -> int:
        # Default to 4 connections for small files, up to 12 for files > 100MB
        if file_size > full_size:
            return max_count
        return max(4, math.ceil((file_size / full_size) * max_count))

    async def _init_download(self, connections: int, file: TypeLocation, part_count: int,
                             part_size: int) -> None:
        minimum, remainder = divmod(part_count, connections)

        def get_part_count() -> int:
            nonlocal remainder
            if remainder > 0:
                remainder -= 1
                return minimum + 1
            return minimum

        # The first sender will export/import authorization, so establish it first
        first_sender = await self._create_download_sender(file, 0, part_size, connections * part_size, get_part_count())
        
        # Then create other senders in parallel
        other_senders = await asyncio.gather(*[
            self._create_download_sender(file, i, part_size, connections * part_size, get_part_count())
            for i in range(1, connections)
        ])
        
        self.senders = [first_sender] + list(other_senders)

    async def _create_download_sender(self, file: TypeLocation, index: int, part_size: int,
                                      stride: int, part_count: int) -> DownloadSender:
        return DownloadSender(self.client, await self._create_sender(), file, index * part_size, part_size,
                              stride, part_count)

    async def _create_sender(self) -> MTProtoSender:
        dc = await self.client._get_dc(self.dc_id)
        sender = MTProtoSender(self.auth_key, loggers=self.client._log)
        await sender.connect(self.client._connection(dc.ip_address, dc.port, dc.id,
                                                     loggers=self.client._log,
                                                     proxy=self.client._proxy))
        if not self.auth_key:
            log.debug(f"Exporting auth to DC {self.dc_id}")
            auth = await self.client(ExportAuthorizationRequest(self.dc_id))
            self.client._init_request.query = ImportAuthorizationRequest(id=auth.id,
                                                                         bytes=auth.bytes)
            req = InvokeWithLayerRequest(LAYER, self.client._init_request)
            await sender.send(req)
            self.auth_key = sender.auth_key
        return sender

    async def download(self, file: TypeLocation, file_size: int,
                       part_size_kb: Optional[float] = None,
                       connection_count: Optional[int] = None) -> AsyncGenerator[bytes, None]:
        connection_count = connection_count or self._get_connection_count(file_size)
        
        # Calculate part size aligned with Telegram boundaries (usually 512KB for large files)
        part_size = (part_size_kb or utils.get_appropriated_part_size(file_size)) * 1024
        part_count = math.ceil(file_size / part_size)
        
        log.debug(f"Starting parallel download: {connection_count} connections, part size {part_size} bytes, total parts {part_count}")
        await self._init_download(connection_count, file, part_count, part_size)

        part = 0
        while part < part_count:
            tasks = []
            for sender in self.senders:
                tasks.append(self.loop.create_task(sender.next()))
            for task in tasks:
                data = await task
                if data is None:
                    break
                yield data
                part += 1
                
        await self._cleanup()
