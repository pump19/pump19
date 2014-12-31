#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
command.py

Handle commands received on IRC.

Copyright (c) 2014 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import aiohttp
import asyncio
import bs4
import datetime
import feedparser
import functools
import logging
import time

PATREON_URL = "http://www.patreon.com/loadingreadyrun"
LRR_RSS_URL = "http://feeds.feedburner.com/Loadingreadyrun"


class CommandHandler(object):
    """
    The command handler interacts with an IRC client and dispatches commands.
    It registers itself as a handler for PRIVMSG events.
    """
    logger = logging.getLogger("command")

    class rate_limit(object):
        """A decorator that suppresses method calls within a certain delay."""
        last = 0.0

        def __init__(self, delay=30):
            """Initialize rate limiter with a default delay of 30."""
            self.delay = delay

        def __call__(self, func):

            @functools.wraps(func)
            @asyncio.coroutine
            def wrapper(*args, **kwargs):
                now = time.monotonic()
                if (now - self.last) > self.delay:
                    self.last = now
                    yield from func(*args, **kwargs)
            return wrapper

    def __init__(self, protocol, **kwargs):
        """Initialize the command handler and register for PRIVMSG events."""
        self.logger.info("Creating CommandHandler instance.")

        self.prefix = kwargs["prefix"]
        self.protocol = protocol
        self.protocol.event_handler("PRIVMSG")(self.handle_privmsg)

    @asyncio.coroutine
    def handle_privmsg(self, nick, target, message):
        """
        Handle a PRIVMSG event and dispatch any command to the relevant method.
        """
        # ignore everything that's not a command with our prefix
        if not message.startswith(self.prefix):
            return

        # command is always separated by a space
        parts = message.split(" ", 1)
        cmd = parts[0]
        args = parts[1].strip() if len(parts) == 2 else None

        self.logger.info("Got command {0} from {1}.".format(cmd, nick))

        # is this a query? if so, send messages to nick instead
        if target == self.protocol.nickname:
            target = nick

        # check if we can handle that command
        cmd_name = "handle_command_{0}".format(cmd[1:])
        handle_command = getattr(self, cmd_name, None)
        if handle_command and callable(handle_command):
            yield from handle_command(target, nick, args)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_patreon(self, target, nick, args):
        """
        Handler !patreon command.
        Post the number of patrons and the total earnings per month.
        """
        patreon_req = yield from aiohttp.client.request("get", PATREON_URL)
        patreon_body = yield from patreon_req.text()
        patreon_soup = bs4.BeautifulSoup(patreon_body)
        tag_patrons = patreon_soup.find("div", id="totalPatrons")
        nof_patrons = tag_patrons.string if tag_patrons else "N/A"

        tag_earnings = patreon_soup.find("span", id="totalEarnings")
        total_earnings = tag_earnings.string if tag_earnings else "N/A"

        patreon_msg = "{0} patrons for a total of ${1} per month. {2}".format(
            nof_patrons, total_earnings, PATREON_URL)

        yield from self.protocol.privmsg(target, patreon_msg)

    @rate_limit()
    @asyncio.coroutine
    def handle_command_feed(self, target, nick, args):
        """
        Handler !feed command.
        Post the most recent video RSS feed item.
        """
        feed_req = yield from aiohttp.client.request(
            "get", LRR_RSS_URL, headers={"Accept": "application/rss+xml"})
        feed_body = yield from feed_req.text()
        feed = feedparser.parse(feed_body)
        latest = feed.entries[0]
        time = datetime.datetime(*latest.published_parsed[:6])

        feed_msg = "LRR Video Feed: {0} ({1}) [{2}]".format(
            latest.title, latest.id, time.isoformat(" "))
        yield from self.protocol.privmsg(target, feed_msg)
