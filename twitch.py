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
import logging
import os

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
CHATTERS_URL = "http://tmi.twitch.tv/group/user/{stream}/chatters"
VIDEOS_URL = ("https://api.twitch.tv/kraken/channels/"
              "{stream}/videos?limit={limit}&broadcast_type={bc_type}")
STREAM_URL = "https://api.twitch.tv/kraken/streams/loadingreadyrun"
GAMES_TOP_URL = ("https://api.twitch.tv/kraken/games/top"
                 "?limit={limit}&offset={offset}")

TWITCH_API_HEADERS = {
    "Accept": "application/vnd.twitchtv.v5+json",
    "Client-ID": CLIENT_ID
}


async def get_broadcasts(stream, limit, loop=None):
    """
    Request the latest n broadcasts for a given stream.
    Returns an iterable of broadcasts, each entry being a tuple of title, url
    and date.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} broadcast(s) for {stream}.".format(
        stream=stream, limit=limit))

    bc_url = VIDEOS_URL.format(stream=stream, limit=limit, bc_type="archive")
    with aiohttp.ClientSession(
            read_timeout=30, headers=TWITCH_API_HEADERS,
            loop=loop) as client:

        bc_req = await client.get(bc_url)
        broadcasts = await bc_req.json(encoding="utf-8")

    logger.debug("Retrieved {nof} broadcasts for {stream}.".format(
        nof=len(broadcasts["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in broadcasts["videos"])


async def get_highlights(stream, limit, loop=None):
    """
    Request the latest n highlights for a given stream.
    Returns an iterable of highlights, each entry being a tuple of title, url
    and date.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} highlight(s) for {stream}.".format(
        stream=stream, limit=limit))

    hl_url = VIDEOS_URL.format(stream=stream, limit=limit, bc_type="highlight")
    with aiohttp.ClientSession(
            read_timeout=30, headers=TWITCH_API_HEADERS,
            loop=loop) as client:

        hl_req = await client.get(hl_url)
        highlights = await hl_req.json(encoding="utf-8")

    logger.debug("Retrieved {nof} highlights for {stream}.".format(
        nof=len(highlights["videos"]), stream=stream))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in highlights["videos"])


async def get_top_games(limit, offset, loop=None):
    """
    Request the games currently viewed the most.
    Returns an iterable of games, each entry being a tuple of id, name and
    number of viewers.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} game(s) starting from #{offset}.".format(
        limit=limit, offset=offset))

    gt_url = GAMES_TOP_URL.format(limit=limit, offset=offset)
    with aiohttp.ClientSession(
            read_timeout=30, headers=TWITCH_API_HEADERS,
            loop=loop) as client:

        gt_req = await client.get(gt_url)
        games = await gt_req.json(encoding="utf-8")

    logger.debug("Retrieved top {nof} games starting from #{offset}.".format(
        nof=len(games["top"]), offset=offset))

    return ((entry["game"]["_id"], entry["game"]["name"], entry["viewers"])
            for entry in games["top"])
