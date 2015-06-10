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
import xml.etree.ElementTree as ET

from os import environ
from urllib.parse import urlencode

LAST_FM_API_KEY = environ["LAST_FM_API_KEY"]
LAST_FM_API_URL = "http://ws.audioscrobbler.com/2.0/"
RDIO_TOKEN_ENDPOINT = "https://services.rdio.com/oauth2/token"
RDIO_RESOURCE_ENDPOINT = "https://services.rdio.com/api/1/"


class Rdio:
    """Simple rdio API client."""

    def __init__(self, client_id, client_secret, loop=None):
        """Setup an OAUTH2 client instance with supplied credentials."""
        # we'll need those credentials for getting access tokens
        self.credentials = aiohttp.BasicAuth(client_id, client_secret)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.client = aiohttp.ClientSession(loop=loop, headers=headers)

    @asyncio.coroutine
    def get_access_token(self):
        """Get an access token using the Client Credentials method."""
        data = {"grant_type": "client_credentials"}
        token_resp = yield from self.client.post(
                RDIO_TOKEN_ENDPOINT, data=data, auth=self.credentials)

        token_data = yield from token_resp.json()
        token = token_data.get("access_token")
        return token

    @asyncio.coroutine
    def oauth_POST(self, method, params):
        """Send an authenticated POST call and return a aiorequest object."""
        # first we need to get an access token
        token = yield from self.get_access_token()

        # we need to add the token and the method itself
        params["access_token"] = token
        params["method"] = method

        request = yield from self.client.post(
                RDIO_RESOURCE_ENDPOINT, data=params)

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
