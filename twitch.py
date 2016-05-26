#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
twitch.py

File containing Twitch API utility functions.
It sets up logging and provides coroutines for querying Twitch.tv APIs.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import aiohttp
import asyncio
import logging
import os

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
CHATTERS_URL = "http://tmi.twitch.tv/group/user/{stream}/chatters"
BROADCAST_URL = ("https://api.twitch.tv/kraken/channels/"
                 "{stream}/videos?limit={limit}&broadcasts=true")
HIGHLIGHT_URL = ("https://api.twitch.tv/kraken/channels/"
                 "{stream}/videos?limit={limit}&broadcasts=false")
STREAM_URL = "https://api.twitch.tv/kraken/streams/loadingreadyrun"
GAMES_TOP_URL = ("https://api.twitch.tv/kraken/games/top"
                 "?limit={limit}&offset={offset}")

TWITCH_API_HEADERS = {
    "Accept": "application/vnd.twitchtv.v3+json",
    "Client-ID": CLIENT_ID
}


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
        "get", bc_url, headers=TWITCH_API_HEADERS)
    broadcasts = yield from bc_req.json()

    logger.debug("Retrieved {nof} broadcasts for {stream}.".format(
        nof=len(broadcasts["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in broadcasts["videos"])


@asyncio.coroutine
def get_highlights(stream, limit):
    """
    Request the latest n highlights for a given stream.
    Returns an iterable of highlights, each entry being a tuple of title, url
    and date.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} highlight(s) for {stream}.".format(
        stream=stream, limit=limit))

    hl_url = HIGHLIGHT_URL.format(stream=stream, limit=limit)
    hl_req = yield from aiohttp.request(
        "get", hl_url, headers=TWITCH_API_HEADERS)
    highlights = yield from hl_req.json()

    logger.debug("Retrieved {nof} highlights for {stream}.".format(
        nof=len(highlights["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in highlights["videos"])


@asyncio.coroutine
def get_top_games(limit, offset):
    """
    Request the games currently viewed the most.
    Returns an iterable of games, each entry being a tuple of name and number
    of viewers.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} game(s) starting from {offset}.".format(
        limit=limit, offset=offset))

    gt_url = GAMES_TOP_URL.format(limit=limit, offset=offset)
    gt_req = yield from aiohttp.request(
        "get", gt_url, headers=TWITCH_API_HEADERS)

    games = yield from gt_req.json()

    logger.debug("Retrieved top {nof} games starting from {offset}.".format(
        nof=len(games["top"]), offset=offset))

    return ((entry["game"]["name"], entry["viewers"])
            for entry in games["top"])


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
        "get", chatters_url, headers=TWITCH_API_HEADERS)
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
    # add a cache if we don't already have one
    if not hasattr(is_moderator, "cache"):
        is_moderator.cache = list()

    key = (stream, user)
    if key in is_moderator.cache:
        return True
    else:
        # we don't know those, query twitch
        mods = yield from get_moderators(stream)
        if user in mods:
            is_moderator.cache.append(key)
            return True
        else:
            return False
