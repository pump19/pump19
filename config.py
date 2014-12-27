#!/usr/bin/env python2
# vim:fenc=utf-8:ts=8:et:sw=4:sts=4:tw=79:ft=python

"""
config.py

The PearBot IRC bot configuration loader.
It reads configuratiom from environment variables and provides access to
component specific dictionaries.

Copyright (c) 2014 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

from os import getenv


def __get_irc_config():
    """Get a configuration dictionary for IRC specific settings."""
    channel_list = getenv("PEARBOT_IRC_CHANNELS")
    channels = channel_list.split(";")
    use_ssl = bool(getenv("PEARBOT_IRC_SSL", True))

    return {"hostname": getenv("PEARBOT_IRC_HOSTNAME"),
            "port": getenv("PEARBOT_IRC_PORT", 6697),
            "ssl": use_ssl,
            "password": getenv("PEARBOT_IRC_PASSWORD"),
            "nickname": getenv("PEARBOT_IRC_NICKNAME", "PearBot"),
            "username": getenv("PEARBOT_IRC_USERNAME", "pearbot"),
            "realname": getenv("PEARBOT_IRC_REALNAME", "PearBot IRC Bot"),
            "channels": channels}


def get_config(component):
    """
    Get a configuration dictionary for a specific component.
    Valid components are:
    - irc
    """
    if component == "irc":
        return __get_irc_config()

    # we don't know that config
    raise KeyError("No such component: {0}".format(component))
