#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
dbutils.py

Various database driven utility functions.

Copyright (c) 2018 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import asyncio
import aiopg

from os import environ

DSN = environ["DATABASE_DSN"]


async def get_pool(loop=None):
    async with get_pool._lock:
        if not get_pool._pool:
            pool = await aiopg.create_pool(
                    DSN, minsize=1, maxsize=5, loop=loop)
            get_pool._pool = pool

        return get_pool._pool
get_pool._pool = None
get_pool._lock = asyncio.Lock()
