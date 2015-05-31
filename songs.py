#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
songs.py

Utilities for querying Rdio and Last.fm

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import aiohttp
import asyncio
import oauthlib.oauth1
import xml.etree.ElementTree as ET

from os import environ
from urllib.parse import urlencode

LAST_FM_API_KEY = environ["LAST_FM_API_KEY"]
LAST_FM_API_URL = "http://ws.audioscrobbler.com/2.0/"
RDIO_API_URL = "http://api.rdio.com/1/"


class Rdio:
    """Simple rdio API client."""

    def __init__(self, key, secret):
        """Setup an OAUTH1 client instance with supplied credentials."""
        self._client = oauthlib.oauth1.Client(key, client_secret=secret)

    @asyncio.coroutine
    def oauth_POST(self, method, params, headers=dict()):
        """Send an oauth signed POST call and return a aiorequest object."""
        # we need to add the API method itself
        params["method"] = method

        # we want to pass a dict, so we need to set the Content-Type
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        # create a signed request
        uri, headers, body = self._client.sign(
                RDIO_API_URL, http_method="POST", body=params, headers=headers)
        request = yield from aiohttp.request(
                "POST", uri, data=body, headers=headers)

        return request

    @asyncio.coroutine
    def findUser(self, *, email=None, vanityName=None, extras=None):
        """The findUser rdio API call."""
        # only email OR vanityName may be set
        if email and vanityName:
            raise ValueError("email and vanityName are mutually exclusive.")
        # one of these MUST be set though
        if not email and not vanityName:
            raise ValueError("Either email or vanityName have to be set.")

        # set up params
        params = dict()
        if email:
            params["email"] = email
        if vanityName:
            params["vanityName"] = vanityName
        if extras:
            params["extras"] = ",".join(extras)

        # get the request
        request = yield from self.oauth_POST("findUser", params)

        # get the json response
        user_data = yield from request.json()
        return user_data


@asyncio.coroutine
def get_lastfm_info(user_name):
    """Get information on a last.fm user."""
    info_qs = urlencode({"method": "user.getInfo",
                         "user": user_name,
                         "api_key": LAST_FM_API_KEY})
    info_url = "{url}?{qs}".format(url=LAST_FM_API_URL, qs=info_qs)
    info_response = yield from aiohttp.request("GET", info_url)
    if info_response.status is not 200:
        return None

    info_raw = yield from info_response.text(encoding="utf-8")
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
    song_response = yield from aiohttp.request("GET", song_url)
    if song_response.status is not 200:
        return result

    song_raw = yield from song_response.text(encoding="utf-8")
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
