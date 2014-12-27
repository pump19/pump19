#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
protocol.py

Provides IRC client functionality based on the bottom module.

Copyright (c) 2014 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import asyncio
import bottom
import logging

# bottom is too talkative, disable its logger
bottom_logger = logging.getLogger("bottom")
bottom_logger.propagate = False
bottom_logger.addHandler(logging.NullHandler())


class Protocol(object):
    """IRC client class."""
    logger = logging.getLogger("protocol")
    restart = True

    def __init__(self, **kwargs):
        """
        Initialize the actual IRC client and register callback methods.
        """
        self.logger.info("Creating Protocol instance.")

        self.nickname = kwargs.get("nickname")
        self.password = kwargs.get("password")
        self.username = kwargs.get("username")
        self.realname = kwargs.get("realname")
        self.channels = kwargs.get("channels")

        self.logger.debug("Registering callback methods.")
        self.irc = bottom.Client(kwargs.get("hostname"),
                                 kwargs.get("port"),
                                 ssl=kwargs.get("ssl"))

        self.irc.on("PING")(self.keepalive)
        self.irc.on("CLIENT_CONNECT")(self.register)
        self.irc.on("CLIENT_DISCONNECT")(self.reconnect)
        self.irc.on("RPL_WELCOME")(self.join)

    @asyncio.coroutine
    def keepalive(self, message):
        """Handle PING messages."""
        self.irc.send("PONG", message=message)

    @asyncio.coroutine
    def register(self):
        """Register with configured nick, user and real name."""
        self.logger.info("Connection established.")
        self.logger.info("Registering with nick {0}.".format(self.nickname))
        if self.password:
            self.irc.send("PASS", password=self.password)
        self.irc.send("NICK", nick=self.nickname)
        self.irc.send("USER", user=self.username, realname=self.realname)

    @asyncio.coroutine
    def join(self):
        """Join configured channels after registering with the network."""
        self.logger.info("Joining channels {0}.".format(
            ",".join(self.channels)))
        for channel in self.channels:
            self.irc.send("JOIN", channel=channel)

    @asyncio.coroutine
    def reconnect(self):
        """Reconnect after losing the connection to the network."""
        if self.restart:
            self.logger.warning("Connection to server lost. Reconnecting...")
            yield from self.irc.connect()
        else:
            self.logger.info("Connection to server closed.")

    @asyncio.coroutine
    def run(self):
        """Run the protocol instance."""
        yield from self.irc.run()

    def shutdown(self):
        """Shut down the protocol instance."""
        self.logger.info("Shutting down protocol instance.")
        self.restart = False
        self.irc.send("QUIT")
