#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
quotes.py

Quotation management functions.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import asyncio
import database

POOL = None
POOL_LOCK = asyncio.Lock()


@asyncio.coroutine
def get_pool():
    global POOL
    if not POOL:
        with (yield from POOL_LOCK):
            POOL = yield from database.create_pool(minsize=0, maxsize=2)

    return POOL


@asyncio.coroutine
def get_quote(*, qid=None, attrib=None):
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        if qid:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE qid = %(qid)s
                        LIMIT 1;"""

            yield from cur.execute(query, {"qid": qid})
        elif attrib:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
                        WHERE attrib_name ~~* %(attrib)s
                        ORDER BY random()
                        LIMIT 1;"""

            search = "%{attrib}%".format(attrib=attrib)
            yield from cur.execute(query, {"attrib": search})
        else:
            query = """SELECT qid, quote, attrib_name, attrib_date
                        FROM quotes
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
def del_quote(qid):
    pool = yield from get_pool()
    with (yield from pool.cursor()) as cur:
        query = "DELETE FROM quotes WHERE qid = %(qid)s;"
        yield from cur.execute(query, {"qid": qid})
