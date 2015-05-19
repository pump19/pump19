#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
rdio.py

Simple Rdio client based on aioauth-client.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

# from aioauth_client import OAuth1Client
import aiohttp
import asyncio
import oauthlib.oauth1

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
