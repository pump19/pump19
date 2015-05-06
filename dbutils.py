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
def get_quote(*, qid=None, keyword=None, attrib=None):
    """Get a single quote, either random or selected by qid or attribution."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        if qid:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE qid = %(qid)s AND deleted = FALSE
                        LIMIT 1;"""

            yield from cur.execute(query, {"qid": qid})
        elif keyword:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE quote ~~* %(keyword)s AND deleted = FALSE
                        ORDER BY random()
                        LIMIT 1;"""

            search = "%{keyword}%".format(keyword=keyword)
            yield from cur.execute(query, {"keyword": search})
        elif attrib:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE attrib_name ~~* %(attrib)s AND deleted = FALSE
                        ORDER BY random()
                        LIMIT 1;"""

            search = "%{attrib}%".format(attrib=attrib)
            yield from cur.execute(query, {"attrib": search})
        else:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE deleted = FALSE
                        ORDER BY random()
                        LIMIT 1;"""

            yield from cur.execute(query)

        if not cur.rowcount:
            return (None, None, None, None)
        else:
            (qid, quote, name, date) = yield from cur.fetchone()
            return (qid, quote, name, date)


@asyncio.coroutine
def add_quote(quote, *, attrib_name=None, attrib_date=None):
    """Add a new quote with optional attribuation."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = """INSERT INTO quotes (quote, attrib_name, attrib_date)
                   VALUES (%(quote)s, %(attrib_name)s, %(attrib_date)s)
                   RETURNING qid, quote, attrib_name, attrib_date;"""

        yield from cur.execute(query, {"quote": quote,
                                       "attrib_name": attrib_name,
                                       "attrib_date": attrib_date})

        (qid, quote, name, date) = yield from cur.fetchone()
        return (qid, quote, name, date)


@asyncio.coroutine
def mod_quote(qid, quote, *, attrib_name=None, attrib_date=None):
    """Modify an existing quote with optional attribution."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = """UPDATE quotes
                   SET quote = %(quote)s,
                       attrib_name = %(attrib_name)s,
                       attrib_date = %(attrib_date)s
                   WHERE qid = %(qid)s AND deleted = FALSE
                   RETURNING qid, quote, attrib_name, attrib_date;"""

        yield from cur.execute(query, {"qid": qid,
                                       "quote": quote,
                                       "attrib_name": attrib_name,
                                       "attrib_date": attrib_date})

        if not cur.rowcount:
            return (None, None, None, None)
        else:
            (qid, quote, name, date) = yield from cur.fetchone()
            return (qid, quote, name, date)


@asyncio.coroutine
def del_quote(qid):
    """Mark a single quote as deleted."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = "UPDATE quotes SET deleted = TRUE WHERE qid = %(qid)s;"
        yield from cur.execute(query, {"qid": qid})

        return True if cur.rowcount else False


@asyncio.coroutine
def rate_quote(qid, voter, good):
    """Rate a single quote as either good or bad."""
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = "SELECT merge_quote_rating(%(qid)s, %(voter)s, %(good)s);"
        yield from cur.execute(
                query, {"qid": qid, "voter": voter, "good": good})


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
