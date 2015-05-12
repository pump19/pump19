#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
dbutils.py

Various database driven utility functions.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import asyncio
import aiopg

from Crypto.Cipher import ARC2
from os import environ

DSN = environ["DATABASE_DSN"]

CODEFALL_CIPHER = ARC2.new(environ["CODEFALL_SECRET"], ARC2.MODE_ECB)
CODEFALL_SHOW_URL = environ["CODEFALL_SHOW_URL"]


@asyncio.coroutine
def get_pool():
    with (yield from get_pool._lock):
        if not get_pool._pool:
            pool = yield from aiopg.create_pool(DSN, minsize=1, maxsize=5)
            get_pool._pool = pool

        return get_pool._pool
get_pool._pool = None
get_pool._lock = asyncio.Lock()


@asyncio.coroutine
def get_codefall_entry(user_name):
    """Get a codefall entry added by a given user."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = """SELECT cid, description, code_type
                   FROM codefall
                   WHERE user_name = %(user_name)s AND claimed = False
                   ORDER BY random();"""
        yield from cur.execute(query, {"user_name": user_name})

        if not cur.rowcount:
            return (None, None, None)
        else:
            (cid, description, code_type) = yield from cur.fetchone()
            raw = cid.to_bytes(ARC2.block_size, byteorder="big")
            msg = CODEFALL_CIPHER.encrypt(raw)
            secret = int.from_bytes(msg, byteorder="big")
            secret_url = CODEFALL_SHOW_URL.format(secret=secret)
            return (secret_url, description, code_type)
