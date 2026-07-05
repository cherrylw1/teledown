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

    def __init__(self, client: TelegramClient, sender: MTProtoSender, file: TypeLocation, limit: int) -> None:
        self.sender = sender
        self.client = client
        self.request = GetFileRequest(file, offset=0, limit=limit)

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
    def _get_connection_count(file_size: int, max_count: int = 20,
                               full_size: int = 100 * 1024 * 1024) -> int:
        # Scale connections up to 20 for files > 100MB
        if file_size > full_size:
            return max_count
        return max(4, math.ceil((file_size / full_size) * max_count))

    async def _init_download(self, connections: int, file: TypeLocation, part_size: int) -> None:
        # Establish the first sender first (to export/import authorization)
        first_sender = await self._create_download_sender(file, part_size)
        
        # Then establish other senders in parallel
        other_senders = await asyncio.gather(*[
            self._create_download_sender(file, part_size)
            for _ in range(1, connections)
        ])
        
        self.senders = [first_sender] + list(other_senders)

    async def _create_download_sender(self, file: TypeLocation, part_size: int) -> DownloadSender:
        return DownloadSender(self.client, await self._create_sender(), file, part_size)

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
        await self._init_download(connection_count, file, part_size)

        # Dictionary to buffer downloaded chunks in memory
        downloaded_parts = {}
        part_downloaded_event = asyncio.Event()

        # Shared counter to distribute tasks to workers
        next_part_to_download = 0
        counter_lock = asyncio.Lock()

        async def worker(sender: DownloadSender):
            nonlocal next_part_to_download
            while True:
                async with counter_lock:
                    part_idx = next_part_to_download
                    next_part_to_download += 1

                if part_idx >= part_count:
                    break

                # Point request to the target chunk offset
                sender.request.offset = part_idx * part_size
                
                try:
                    result = await self.client._call(sender.sender, sender.request)
                    downloaded_parts[part_idx] = result.bytes
                    part_downloaded_event.set()
                except Exception as e:
                    log.error(f"Worker failed downloading chunk {part_idx}: {e}")
                    raise e

        # Spawn all worker connections in parallel tasks
        worker_tasks = [
            self.loop.create_task(worker(sender))
            for sender in self.senders
        ]

        # Consuming and yielding in-order chunks
        current_part_to_yield = 0
        while current_part_to_yield < part_count:
            while current_part_to_yield not in downloaded_parts:
                part_downloaded_event.clear()
                
                # Check for worker failures to fail fast
                for task in worker_tasks:
                    if task.done() and task.exception() is not None:
                        await self._cleanup()
                        raise task.exception()
                
                try:
                    await asyncio.wait_for(part_downloaded_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

            yield downloaded_parts.pop(current_part_to_yield)
            current_part_to_yield += 1

        # Gather remaining worker tasks to ensure clean completion
        await asyncio.gather(*worker_tasks)
        await self._cleanup()
