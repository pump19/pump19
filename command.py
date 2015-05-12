#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
command.py

Handle commands received on IRC.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import aiohttp
import aiomc
import asyncio
import bs4
import dbutils
import functools
import logging
import re
import twitch

CODEFALL_URL = "http://pump19.eu/codefall"
COMMAND_URL = "http://pump19.eu/commands"
PATREON_URL = "https://www.patreon.com/loadingreadyrun"

CMD_REGEX = {
    "patreon":
        re.compile("^patreon$"),
    "latest":
        re.compile("^latest"
                   "(?: (?P<feed>video|podcast|broadcast|highlight))?$"),
    "codefall":
        re.compile("^codefall$"),
    "lrrmc":
        re.compile("^lrrmc$"),
    "help":
        re.compile("^help$")
}


class CommandHandler:
    """
    The command handler interacts with an IRC client and dispatches commands.
    It registers itself as a handler for PRIVMSG events.
    """
    logger = logging.getLogger("command")

    class Limiter:
        """
        A decorator that suppresses method calls within a certain time span.
        """

        logger = logging.getLogger("command.limiter")

        def __init__(self, *, span=15, loop=None):
            """Initialize rate limiter with a default delay of 30."""
            self.span = span
            self.loop = loop or asyncio.get_event_loop()

        def __call__(self, func):

            @functools.wraps(func)
            @asyncio.coroutine
            def wrapper(*args, **kwargs):
                now = self.loop.time()
                if (now - wrapper._spam_last) > wrapper._spam_span:
                    wrapper._spam_last = now
                    yield from func(*args, **kwargs)
                else:
                    self.logger.warning("Suppressed call to {name}.".format(
                        name=func.__name__))

            # each wrapper remembers its own delay and last call
            wrapper._spam_span = self.span
            wrapper._spam_last = 0.0

            return wrapper

    rate_limited = Limiter()

    class CommandRouter:
        """A simple router matching strings against a set of regular
           expressions match to a callable."""

        routes = list()

        def add_route(self, regex, callback):
            self.routes.append((regex, callback))

        def get_route(self, string):
            for (regex, callback) in self.routes:
                match = regex.fullmatch(string)
                if not match:
                    continue

                # add matching groups to function
                return functools.partial(callback, **match.groupdict())

            return None

    router = CommandRouter()

    def __init__(self, client, feed, *, prefix="&", override=None):
        """Initialize the command handler and register for PRIVMSG events."""
        self.logger.info("Creating CommandHandler instance.")

        self.prefix = prefix
        self.override = override
        self.client = client
        self.feed = feed
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

    @rate_limited
    @asyncio.coroutine
    def handle_command_patreon(self, target, nick):
        """
        Handle !patreon command.
        Post the number of patrons and the total earnings per month.
        """
        patreon_req = yield from aiohttp.request("get", PATREON_URL)
        patreon_body = yield from patreon_req.read()
        patreon_soup = bs4.BeautifulSoup(patreon_body)
        tag_patrons = patreon_soup.find("div", id="totalPatrons")
        nof_patrons = tag_patrons.string if tag_patrons else "N/A"

        tag_earnings = patreon_soup.find("span", id="totalEarnings")
        total_earnings = tag_earnings.string if tag_earnings else "N/A"

        patreon_msg = "{0} patrons for a total of ${1} per month. {2}".format(
            nof_patrons, total_earnings, PATREON_URL)

        yield from self.client.privmsg(target, patreon_msg)

    @rate_limited
    @asyncio.coroutine
    def handle_command_latest(self, target, nick, *, feed=None):
        """
        Handle !latest [video|podcast|broadcast|highlight] command.
        Post the most recent RSS feed item or Twitch.tv broadcast.
        """
        feed = feed or "video"

        # broadcasts are updated here
        if feed == "broadcast":
            broadcast = yield from twitch.get_broadcasts("loadingreadyrun", 1)
            video = next(broadcast, None)

            broadcast_msg = "Latest Broadcast: {0} ({1}) [{2}]".format(*video)

            yield from self.client.privmsg(target, broadcast_msg)
        elif feed == "highlight":
            highlight = yield from twitch.get_highlights("loadingreadyrun", 1)
            video = next(highlight, None)

            highlight_msg = "Latest Highlight: {0} ({1}) [{2}]".format(*video)

            yield from self.client.privmsg(target, highlight_msg)
        else:
            # start a manual update
            yield from self.feed.update(feed)

            # let the feed parser announce it
            yield from self.feed.announce(feed, target=target)

    @rate_limited
    @asyncio.coroutine
    def handle_command_codefall(self, target, nick):
        """
        Handle !codefall command.
        If available, post a single unclaimed codefall URL.
        """
        (secret_url,
         description,
         code_type) = yield from dbutils.get_codefall_entry(nick)

        if not secret_url:
            no_codefall_msg = ("Could not find any unclaimed codes. "
                               "You can add new entries at {url}.".format(
                                   url=CODEFALL_URL))
            yield from self.client.privmsg(target, no_codefall_msg)
            return

        codefall_msg = "Codefall: {desc} ({ctype}) {url}".format(
                desc=description, ctype=code_type, url=secret_url)

        yield from self.client.privmsg(target, codefall_msg)

    @rate_limited
    @asyncio.coroutine
    def handle_command_lrrmc(self, target, nick):
        """
        Handle !lrrmc command.
        Query and post the status of the LRR Minecraft server.
        """
        # don't stall forever when querying status
        status_coro = aiomc.get_status("rift.dahou.se", 25575)
        try:
            status = yield from asyncio.wait_for(status_coro, 2.0)
        except asyncio.TimeoutError:
            status = None

        base_msg = ("Join the LRR Minecraft Server on lrrmc.rebellious.uno! "
                    "Check http://lrrmap.rebellious.uno/ for the dynamic map. "
                    "Current Status: {status}")

        if not status:
            no_lrrmc_msg = base_msg.format(status="Unknown")
            yield from self.client.privmsg(target, no_lrrmc_msg)
            return

        players = status.get("players", dict())
        nowp = players.get("online", 0)
        maxp = players.get("max", 0)
        status_msg = "Online - {now}/{max} players".format(now=nowp, max=maxp)

        lrrmc_msg = base_msg.format(status=status_msg)
        yield from self.client.privmsg(target, lrrmc_msg)

    @rate_limited
    @asyncio.coroutine
    def handle_command_help(self, target, nick):
        """
        Handle !help command.
        Posts a link to the golem's list of supported commands.
        """
        help_msg = ("Pump19 is run by Twisted Pear. "
                    "Check {url} for a list of supported commands.").format(
                        url=COMMAND_URL)
        yield from self.client.privmsg(target, help_msg)
