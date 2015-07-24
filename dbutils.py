#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
dbutils.py

Various database driven utility functions.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import asyncio
import aiopg
import skippy

from os import environ

DSN = environ["DATABASE_DSN"]

CODEFALL_CIPHER = skippy.Skippy(environ["CODEFALL_SECRET"].encode())
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
def get_codefall_entries(user_name, limit=1):
    """Get a list of unclaimed codefall entries added by a given user."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = """SELECT cid, description, code_type
                   FROM codefall
                   WHERE user_name = %(user_name)s AND claimed = False
                   ORDER BY random()
                   LIMIT %(limit)s;"""
        yield from cur.execute(
                query, {"user_name": user_name, "limit": limit})

        if not cur.rowcount:
            return list()
        else:
            entries = list()
            results = yield from cur.fetchall()
            for (cid, description, code_type) in results:
                secret = CODEFALL_CIPHER.encrypt(cid)
                secret_url = CODEFALL_SHOW_URL.format(secret=secret)
                entries.append((secret_url, description, code_type))
            return entries
