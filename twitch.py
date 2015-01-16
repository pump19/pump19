#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
twitch.py

File containing Twitch API utility functions.
It sets up logging and provides coroutines for querying Twitch.tv APIs.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import asyncio
import aiohttp
import database
import logging

CHATTERS_URL = "http://tmi.twitch.tv/group/user/{stream}/chatters"
BROADCAST_URL = ("https://api.twitch.tv/kraken/channels/"
                 "{stream}/videos?limit={limit}&broadcasts=true")


@asyncio.coroutine
def get_broadcasts(stream, limit):
    """
    Request the latest n broadcasts for a given stream.
    Returns an iterable of broadcasts, each entry being a tuple of title, url
    and date.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} broadcast(s) for {stream}.".format(
        stream=stream, limit=limit))

    bc_url = BROADCAST_URL.format(stream=stream, limit=limit)
    bc_req = yield from aiohttp.request(
        "get", bc_url, headers={"Accept": "application/vnd.twitchtv.v3+json"})
    broadcasts = yield from bc_req.json()

    logger.debug("Retrieved {nof} broadcasts for {stream}.".format(
        nof=len(broadcasts["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in broadcasts["videos"])


@asyncio.coroutine
def get_moderators(stream):
    """
    Request a list of moderators currently online in a given Twitch chat.
    For convenience, the list will contain staff members, admins and global
    moderators as well.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting chatters for {stream}.".format(stream=stream))

    chatters_url = CHATTERS_URL.format(stream=stream)
    chatters_req = yield from aiohttp.request(
        "get", chatters_url, headers={"Accept": "application/json"})
    chatters_dict = yield from chatters_req.json()
    chatters = chatters_dict["chatters"]

    moderators = chatters["moderators"]
    moderators.extend(chatters["staff"])
    moderators.extend(chatters["admins"])
    moderators.extend(chatters["global_mods"])

    logger.debug("Retrieved {nof} moderators for {stream}.".format(
        nof=len(moderators), stream=stream))

    return moderators


@asyncio.coroutine
def is_moderator(stream, user):
    """Check whether a user is a moderator on a given channel."""
    # if we're here, we don't have this one in our cache, query twitch instead
    moderators = yield from get_moderators(stream)
    return True if user in moderators else False
