#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

import aiomc.protocol as protocol
import asyncio
import contextlib
import json
import logging

"""
aiomc.py

Query Minecraft server information using asyncio.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

logger = logging.getLogger("aiomc")
logger.addHandler(logging.NullHandler())


async def get_status(host, port, loop=None):
    try:
        (rd, wr) = await asyncio.open_connection(host, port, loop=loop)
    except OSError:
        logger.error("Error connecting to %s:%d", host, port)
        return None

    logger.info("Established connection to %s:%d", host, port)

    packet = protocol.handshake(host, port)
    wr.write(packet)
    await wr.drain()

    packet = protocol.status_request()
    wr.write(packet)
    await wr.drain()
    length = await protocol.unpack_varint(rd)
    logger.debug("Answer to status request is %d bytes long.", length)

    # make sure to close the socket when we're done
    with contextlib.closing(wr):
        status = await protocol.unpack_varint(rd)
        if status:
            logger.error("Got error code %d for status request.", status)
            return None

        raw = await protocol.unpack_string(rd)
        data = json.loads(raw)
        return data
