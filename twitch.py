#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
twitch.py

File containing Twitch API utility functions.
It sets up logging and provides coroutines for querying Twitch.tv APIs.

Copyright (c) 2018 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import aiohttp
import logging
import os

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
VIDEOS_URL = ("https://api.twitch.tv/kraken/channels/"
              "{channel}/videos?limit={limit}&broadcast_type=archive")
CLIPS_URL = ("https://api.twitch.tv/kraken/clips/top"
             "?channel={channel}&limit={limit}")

TWITCH_API_HEADERS = {
    "Accept": "application/vnd.twitchtv.v5+json",
    "Client-ID": CLIENT_ID
}


async def get_broadcasts(channel, limit, loop=None):
    """
    Request the latest n broadcasts for a given channel.
    Returns an iterable of broadcasts, each entry being a tuple of title, url
    and date.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} broadcast(s) for {channel}.".format(
        channel=channel, limit=limit))

    bc_url = VIDEOS_URL.format(channel=channel, limit=limit)
    with aiohttp.ClientSession(
            read_timeout=30, headers=TWITCH_API_HEADERS,
            loop=loop) as client:

        bc_req = await client.get(bc_url)
        broadcasts = await bc_req.json(encoding="utf-8")

    logger.debug("Retrieved {nof} broadcasts for {channel}.".format(
        nof=len(broadcasts["videos"]), channel=channel))

    return ((video["title"], video["url"], video["recorded_at"])
            for video in broadcasts["videos"])


async def get_top_clips(channel, limit, loop=None):
    """
    Request the top n clips for a given channel.
    """
    logger = logging.getLogger("twitch")
    logger.info("Requesting {limit} clip(s) for {channel}.".format(
        channel=channel, limit=limit))

    tc_url = CLIPS_URL.format(channel=channel, limit=limit)
    with aiohttp.ClientSession(
            read_timeout=30, headers=TWITCH_API_HEADERS,
            loop=loop) as client:

        tc_req = await client.get(tc_url)
        clips = await tc_req.json(encoding="utf-8")

    logger.debug("Retrieved {nof} clips for {channel}.".format(
        nof=len(clips["clips"]), channel=channel))

    return ((clip["title"], clip["slug"], clip["created_at"])
            for clip in clips["clips"])
