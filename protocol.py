#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
protocol.py

Provides IRC client functionality based on the bottom module.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import asyncio
import bottom
import logging

# bottom is too talkative, disable its logger
bottom_logger = logging.getLogger("bottom")
bottom_logger.propagate = False
bottom_logger.addHandler(logging.NullHandler())


class Protocol:
    """IRC client class."""
    logger = logging.getLogger("protocol")
    restart = True
    msglock = asyncio.Lock()

    def __init__(self, *,
                 hostname="localhost", port=6667, ssl=False,
                 nickname=None, username=None, realname=None, password=None,
                 channels=[]):
        """
        Initialize the actual IRC client and register callback methods.
        """
        self.logger.info("Creating Protocol instance.")

        self.nickname = nickname
        self.password = password
        self.username = username
        self.realname = realname
        self.channels = channels

        self.logger.debug("Registering callback methods.")
        self.irc = bottom.Client(hostname, port, ssl=ssl)

        self.event_handler("PING")(self.keepalive)
        self.event_handler("CLIENT_CONNECT")(self.register)
        self.event_handler("CLIENT_DISCONNECT")(self.reconnect)
        self.event_handler("RPL_WELCOME")(self.join)

    @property
    def loop(self):
        """Expose the bottom Client's event loop."""
        return self.irc.loop

    def event_handler(self, command):
        """Register an event handler."""
        return self.irc.on(command)

    async def privmsg(self, target, message):
        """
        Send a message to target (nick or channel).
        This method is rate limited to one line per second.
        """
        async with self.msglock:
            self.irc.send("PRIVMSG", target=target, message=message)
            await asyncio.sleep(1)

    async def announce(self, message):
        """
        Send a message to all registered channels.
        This method is rate limited to one line per second.
        """
        async with self.msglock:
            for channel in self.channels:
                self.irc.send("PRIVMSG", target=channel, message=message)
                await asyncio.sleep(1)

    async def keepalive(self, message):
        """Handle PING messages."""
        self.irc.send("PONG", message=message)

    async def register(self):
        """Register with configured nick, user and real name."""
        self.logger.info("Connection established.")
        self.logger.info("Registering with nick {0}.".format(self.nickname))
        if self.password:
            self.irc.send("PASS", password=self.password)
        self.irc.send("NICK", nick=self.nickname)
        self.irc.send("USER", user=self.username, realname=self.realname)

    async def join(self, **kwargs):
        """Join configured channels after registering with the network."""
        self.logger.info("Joining channels {0}.".format(
            ",".join(self.channels)))
        for channel in self.channels:
            self.irc.send("JOIN", channel=channel)

    async def reconnect(self):
        """Reconnect after losing the connection to the network."""
        if self.restart:
            self.logger.warning("Connection to server lost. Reconnecting...")
            await self.irc.connect()
        else:
            self.logger.info("Connection to server closed.")
            self.loop.stop()

    def start(self):
        """Run the protocol instance."""
        self.loop.create_task(self.irc.connect())

    def shutdown(self):
        """Shut down the protocol instance."""
        self.logger.info("Shutting down protocol instance.")
        self.restart = False
        self.irc.send("QUIT")
