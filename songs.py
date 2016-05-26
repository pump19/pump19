#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
songs.py

Utilities for querying Last.fm

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import aiohttp
import xml.etree.ElementTree as ET

from os import environ
from urllib.parse import urlencode

LAST_FM_API_KEY = environ["LAST_FM_API_KEY"]
LAST_FM_API_URL = "http://ws.audioscrobbler.com/2.0/"


async def get_lastfm_info(user_name, loop=None):
    """Get information on a last.fm user."""
    info_qs = urlencode({"method": "user.getInfo",
                         "user": user_name,
                         "api_key": LAST_FM_API_KEY})
    info_url = "{url}?{qs}".format(url=LAST_FM_API_URL, qs=info_qs)
    info_response = await aiohttp.request("GET", info_url, loop=loop)
    if info_response.status is not 200:
        return None

    info_raw = await info_response.text(encoding="utf-8")
    info_root = ET.XML(info_raw)
    if info_root.get("status") != "ok":
        return None

    real_name = info_root.findtext("user/realname")
    result = {"name": real_name or user_name}

    song_qs = urlencode({"method": "user.getRecentTracks",
                         "user": user_name,
                         "limit": 1,
                         "api_key": LAST_FM_API_KEY})
    song_url = "{url}?{qs}".format(url=LAST_FM_API_URL, qs=song_qs)
    song_response = await aiohttp.request("GET", song_url, loop=loop)
    if song_response.status is not 200:
        return result

    song_raw = await song_response.text(encoding="utf-8")
    song_root = ET.XML(song_raw)
    if song_root.get("status") != "ok":
        return result

    track = song_root.find("recenttracks/track")
    if not track:
        return result

    result["live"] = track.get("nowplaying", False)
    result["artist"] = track.findtext("artist", "N/A")
    result["track"] = track.findtext("name", "N/A")

    return result
