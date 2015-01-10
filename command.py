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
import functools
import logging

PATREON_URL = "http://www.patreon.com/loadingreadyrun"
BROADCAST_URL = ("https://api.twitch.tv/kraken/channels/"
                 "loadingreadyrun/videos?limit=1&broadcasts=true")


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

    def __init__(self, client, feed, *, prefix="!"):
        """Initialize the command handler and register for PRIVMSG events."""
        self.logger.info("Creating CommandHandler instance.")

        self.prefix = prefix
        self.client = client
        self.feed = feed
        self.client.event_handler("PRIVMSG")(self.handle_privmsg)

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
        if target == self.client.nickname:
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
    def handle_command_latest(self, target, nick, args):
        """
        Handle !latest [video|podcast|broadcast] command.
        Post the most recent RSS feed item or Twitch.tv broadcast.
        """
        feed = "video"
        if args and args in ["video", "podcast", "broadcast"]:
            feed = args

        # broadcasts are updated here
        if feed == "broadcast":
            broadcast_req = yield from aiohttp.request(
                "get", BROADCAST_URL,
                headers={"Accept": "application/vnd.twitchtv.v3+json"})
            broadcast = yield from broadcast_req.json()
            video = broadcast["videos"][0]

            broadcast_msg = "Latest Broadcast: {0} ({1}) [{2}]".format(
                video["title"], video["url"], video["recorded_at"])

            yield from self.client.privmsg(target, broadcast_msg)
        else:
            # start a manual update
            yield from self.feed.update(feed)

            # let the feed parser announce it
            yield from self.feed.announce(feed, target=target)
