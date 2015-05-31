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
import enum
import logging
import re

CHATTERS_URL = "http://tmi.twitch.tv/group/user/{stream}/chatters"
BROADCAST_URL = ("https://api.twitch.tv/kraken/channels/"
                 "{stream}/videos?limit={limit}&broadcasts=true")
HIGHLIGHT_URL = ("https://api.twitch.tv/kraken/channels/"
                 "{stream}/videos?limit={limit}&broadcasts=false")
STREAM_URL = "https://api.twitch.tv/kraken/streams/loadingreadyrun"


class Streamers(enum.Enum):
    Offline = 1
    Unknown = 2
    Adam = 3
    Alex = 4
    Beej = 5
    Cameron = 6
    Graham = 7
    Heather = 8
    Ian = 9
    James = 10
    Kathleen = 11
    Paul = 12

SHOW_HOSTS = (
    (re.compile("Gamehaüs", re.I),
        Streamers.Adam),
    (re.compile("Cameron", re.I),
        Streamers.Cameron),
    (re.compile("Beej's Backlog", re.I),
        Streamers.Beej),
    (re.compile("CheckPoint", re.I),
        Streamers.Graham, Streamers.Kathleen, Streamers.Paul),
    (re.compile("IDDQDerp", re.I),
        Streamers.Alex),
    (re.compile("GPLP", re.I),
        Streamers.Graham, Streamers.Paul),
    (re.compile("Heather's Handhelds", re.I),
        Streamers.Heather),
    (re.compile("House of Stark", re.I),
        Streamers.Graham),
    (re.compile("I, Horner", re.I),
        Streamers.Ian),
    (re.compile("Kathleen", re.I),
        Streamers.Kathleen),
    (re.compile("LRRMtg", re.I),
        Streamers.Graham, Streamers.James),
    (re.compile("Let's NOPE", re.I),
        Streamers.Alex),
    (re.compile("Things on My Stream", re.I),
        Streamers.Paul),
    (re.compile("Video Games w/ Video James", re.I),
        Streamers.James)
)


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
        "get", hl_url, headers={"Accept": "application/vnd.twitchtv.v3+json"})
    highlights = yield from hl_req.json()

    logger.debug("Retrieved {nof} highlights for {stream}.".format(
        nof=len(highlights["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in highlights["videos"])


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


@asyncio.coroutine
def get_streamer():
    """Get the current streamer (if any) for loadingreadyrun Twitch channel."""
    logger = logging.getLogger("twitch")
    logger.info("Requesting current streamer for loadingreadyrun.")

    # first, get the current stream (if any)
    stream_req = yield from aiohttp.request(
        "get", STREAM_URL,
        headers={"Accept": "application/vnd.twitchtv.v3+json"})
    stream_dict = yield from stream_req.json()
    stream = stream_dict.get("stream", {})
    if not stream:
        return Streamers.Offline

    # check stream.channel.status for current show
    channel = stream.get("channel", {})
    status = channel.get("status")
    if not status:
        return Streamers.Unknown

    # let's see if we can find the current show
    for regex, *hosts in SHOW_HOSTS:
        if regex.search(status):
            return hosts

    return Streamers.Unknown
