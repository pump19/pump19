#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

import asyncio
import contextlib
import logging
import struct
import time

"""
aiomumble.py

Query Mumble server information using asyncio.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

logger = logging.getLogger("aiomumble")
logger.addHandler(logging.NullHandler())


class MumblePingProtocol:
    def __init__(self):
        self.transport = None
        self.status = None
        self.done = asyncio.Event()

    def connection_made(self, transport):
        self.transport = transport
        buf = struct.pack(">id", 0, time.monotonic())
        self.transport.sendto(buf)

    def connection_lost(self, exc):
        pass

    def datagram_received(self, data, addr):
        logger.debug("Answer to ping request is %d bytes long.", len(data))
        (_, t_snd, u_cur, u_max, _) = struct.unpack(">idiii", data)
        ping = 1000 * (time.monotonic() - t_snd)
        self.status = {"ping": ping, "current": u_cur, "max": u_max}
        self.done.set()

    async def get_status(self):
        await self.done.wait()
        return self.status


async def get_status(host, port, loop=None):
    loop = loop or asyncio.get_event_loop()
    (trans, proto) = await loop.create_datagram_endpoint(
            MumblePingProtocol, remote_addr=(host, port))
    logger.info("Established connection to %s:%d", host, port)

    with contextlib.closing(trans):
        status = await proto.get_status()
        return status
