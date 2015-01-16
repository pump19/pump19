#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
command.py

Handle commands received on IRC.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import aiohttp
import asyncio
import bs4
import functools
import logging
import re
import twitch

from psycopg2 import DataError

PATREON_URL = "http://www.patreon.com/loadingreadyrun"

CMD_REGEX = {
    "patreon":
        re.compile("patreon"),
    "latest":
        re.compile("latest(?: (?P<feed>video|podcast|broadcast))?"),
    "quote":
        re.compile("quote(?: (?:(?P<qid>\d+)|(?P<attrib>.+)))?"),
    "addquote":
        re.compile("addquote"
                   "(?: \((?P<attrib_name>.+)\))?"
                   "(?: \[(?P<attrib_date>\d{4}-[01]\d-[0-3]\d)\])?"
                   "(?: (?P<quote>.+))"),
    "delquote":
        re.compile("delquote (?P<qid>\d+)")
}


class CommandHandler(object):
    """
    The command handler interacts with an IRC client and dispatches commands.
    It registers itself as a handler for PRIVMSG events.
    """
    logger = logging.getLogger("command")

    class rate_limit(object):
        """A decorator that suppresses method calls within a certain delay."""
        last = 0.0

        def __init__(self, *, delay=30, loop=None):
            """Initialize rate limiter with a default delay of 30."""
            self.delay = delay
            self.loop = loop or asyncio.get_event_loop()

        def __call__(self, func):

            @functools.wraps(func)
            @asyncio.coroutine
            def wrapper(*args, **kwargs):
                now = self.loop.time()
                if (now - self.last) > self.delay:
                    self.last = now
                    yield from func(*args, **kwargs)
            return wrapper

    class CommandRouter:
        """A simple router matching strings against a set of regular
           expressions match to a callable."""

        routes = list()

        def add_route(self, regex, callback):
            self.routes.append((regex, callback))

        def get_route(self, string):
            for (regex, callback) in self.routes:
                match = regex.match(string)
                if not match:
                    continue

                # add matching groups to function
                return functools.partial(callback, **match.groupdict())

            return None

    router = CommandRouter()

    def __init__(self, client, feed, dbconn, *, prefix="!"):
        """Initialize the command handler and register for PRIVMSG events."""
        self.logger.info("Creating CommandHandler instance.")

        self.prefix = prefix
        self.client = client
        self.feed = feed
        self.db = dbconn
        self.client.event_handler("PRIVMSG")(self.handle_privmsg)

        self.setup_routing()

    def setup_routing(self):
        """Connect command handlers to regular expressions using the router."""
        for key, regex in CMD_REGEX.items():
            cmd_name = "handle_command_{0}".format(key)
            handle_command = getattr(self, cmd_name, None)
            if handle_command and callable(handle_command):
                self.router.add_route(regex, handle_command)

    @asyncio.coroutine
    def handle_privmsg(self, nick, target, message):
        """
        Handle a PRIVMSG event and dispatch any command to the relevant method.
        """
        # ignore everything that's not a command with our prefix
        if not message.startswith(self.prefix) or len(message) < 2:
            return

        # remove prefix, regex will retrieve the arguments
        cmd = message[1:]

        self.logger.info("Got command \"{0}\" from {1}.".format(cmd, nick))

        # is this a query? if so, send messages to nick instead
        if target == self.client.nickname:
            target = nick

        # check if we can handle that command
        handle_command = self.router.get_route(cmd)
        if handle_command and callable(handle_command):
            yield from handle_command(target, nick)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_patreon(self, target, nick):
        """
        Handle !patreon command.
        Post the number of patrons and the total earnings per month.
        """
        patreon_req = yield from aiohttp.request("get", PATREON_URL)
        patreon_body = yield from patreon_req.text()
        patreon_soup = bs4.BeautifulSoup(patreon_body)
        tag_patrons = patreon_soup.find("div", id="totalPatrons")
        nof_patrons = tag_patrons.string if tag_patrons else "N/A"

        tag_earnings = patreon_soup.find("span", id="totalEarnings")
        total_earnings = tag_earnings.string if tag_earnings else "N/A"

        patreon_msg = "{0} patrons for a total of ${1} per month. {2}".format(
            nof_patrons, total_earnings, PATREON_URL)

        yield from self.client.privmsg(target, patreon_msg)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_latest(self, target, nick, *, feed=None):
        """
        Handle !latest [video|podcast|broadcast] command.
        Post the most recent RSS feed item or Twitch.tv broadcast.
        """
        if not feed:
            feed = "video"

        # broadcasts are updated here
        if feed == "broadcast":
            broadcast = yield from twitch.get_broadcasts("loadingreadyrun", 1)
            video = next(broadcast, None)

            broadcast_msg = "Latest Broadcast: {0} ({1}) [{2}]".format(*video)

            yield from self.client.privmsg(target, broadcast_msg)
        else:
            # start a manual update
            yield from self.feed.update(feed)

            # let the feed parser announce it
            yield from self.feed.announce(feed, target=target)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_quote(self, target, nick, *, qid=None, attrib=None):
        """
        Handle !quote [id] command.
        Post either the specified or a random quote.
        """
        if qid:
            qid = int(qid)

        cur = yield from self.db.cursor()
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
            if qid:
                no_quote_msg = "Could not retrieve quote #{qid}.".format(
                    qid=qid)
            elif attrib:
                no_quote_msg = ("Could not retrieve quote "
                                "matching \"{attrib}\".".format(attrib=attrib))
            else:
                no_quote_msg = "Could not retrieve random quote."

            yield from self.client.privmsg(target, no_quote_msg)
        else:
            (qid, quote, name, date) = yield from cur.fetchone()
            quote_msg = "Quote #{qid}: \"{quote}\"".format(qid=qid,
                                                           quote=quote)
            if name:
                quote_msg += " ~{name}".format(name=name)
            if date:
                quote_msg += " [{date!s}]".format(date=date)

            yield from self.client.privmsg(target, quote_msg)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_addquote(self, target, nick, *, quote=None,
                                attrib_name=None, attrib_date=None):
        """
        Handle !addquote (<attrib_name>) [<attrib_date>] <quote> command.
        Add the provided quote to the database.
        Only moderators may add new quotes.
        """
        if not quote:
            return

        if not (yield from twitch.is_moderator("loadingreadyrun", nick)):
            return

        cur = yield from self.db.cursor()
        query = """INSERT INTO quotes (quote, attrib_name, attrib_date)
                   VALUES (%(quote)s, %(attrib_name)s, %(attrib_date)s)
                   RETURNING qid, quote, attrib_name, attrib_date;"""
        try:
            yield from cur.execute(query, {"quote": quote,
                                           "attrib_name": attrib_name,
                                           "attrib_date": attrib_date})
        except DataError:
            no_quote_msg = "Could not add quote."
            yield from self.client.privmsg(target, no_quote_msg)
        else:
            (qid, quote, name, date) = yield from cur.fetchone()
            quote_msg = "New quote #{qid}: \"{quote}\"".format(qid=qid,
                                                               quote=quote)
            if name:
                quote_msg += " ~{name}".format(name=name)
            if date:
                quote_msg += " [{date!s}]".format(date=date)

            yield from self.client.privmsg(target, quote_msg)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_delquote(self, target, nick, *, qid=None):
        """
        Handle !delquote <qid> command.
        Delete the provided quote ID from the database.
        Only moderators may delete quotes.
        """
        if not qid or not qid.isdigit():
            return
        qid = int(qid)

        if not (yield from twitch.is_moderator("loadingreadyrun", nick)):
            return

        cur = yield from self.db.cursor()
        query = "DELETE FROM quotes WHERE qid = %(qid)s;"
        yield from cur.execute(query, {"qid": qid})
