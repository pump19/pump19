#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
lrrfeed.py

Periodically update LRR RSS feeds and store latest entries.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import aiohttp
import asyncio
import datetime
import feedparser
import logging

RSS_FEEDS = {
    "video": {"title": "LRR Video Feed",
              "url": "http://feeds.feedburner.com/Loadingreadyrun"},
    "podcast": {"title": "LRRcast Feed",
                "url": "http://loadingreadyrun.com/lrrcasts/feed/all"}
    }


class LRRFeedParser:
    """
    The LRR RSS Feed parser manages tasks that update the LRR video and
    LRRcast feeds periodically.
    It stores the latest entry for each and announces any changes it sees.
    """
    logger = logging.getLogger("lrrfeed")
    updater = dict()

    def __init__(self, client, *, delay=300, loop=None):
        """Initialize the LRR RSS feed parser."""
        self.logger.info("LRRFeedParser(delay={0}) created.".format(delay))

        self.delay = delay
        self.client = client
        self.loop = loop or asyncio.get_event_loop()

    def start(self):
        """Start automatic update tasks."""
        for feed in RSS_FEEDS.keys():
            if feed not in self.updater:
                coro = self.auto_update(feed)
                self.updater[feed] = {"task": self.loop.create_task(coro),
                                      "lock": asyncio.Lock(),
                                      "last": 0.0,
                                      "latest": None}
            else:
                self.logger.warning("Automatic update for RSS feed {0} is "
                                    "already running.".format(feed))

    def stop(self):
        """Stop automatic update tasks."""
        tasks = []
        for feed in RSS_FEEDS.keys():
            if feed in self.updater:
                task = self.updater[feed]["task"]
                task.cancel()
                tasks.append(task)
                del self.updater[feed]
            else:
                self.logger.warning("Automatic update for RSS feed {0} is "
                                    "not running.".format(feed))

        self.logger.info("Waiting for automatic update to finish.")
        asyncio.wait(tasks)

    @asyncio.coroutine
    def auto_update(self, feed):
        self.logger.info("Starting automatic update for RSS feed "
                         "{0}.".format(feed))
        try:
            while True:
                # check if we were woken too early (e.g. after a manual update)
                now = self.loop.time()
                nxt = self.updater[feed]["last"] + self.delay
                if nxt > now:
                    # make sure we sleep slightly longer than necessary
                    naptime = 0.1 + (nxt - now)
                    yield from asyncio.sleep(naptime)
                else:
                    yield from self.update(feed)
        except asyncio.CancelledError:
            self.logger.info("Automatic update for RSS feed {0} was "
                             "cancelled.".format(feed))

    @asyncio.coroutine
    def update(self, feed, *, announce=True):
        """
        Do the actual update for a given feed.
        If announce is set to True (default) a change of the "url" key will
        result in the stream being announced on the protocol.
        """
        if feed not in self.updater or feed not in RSS_FEEDS:
            self.logger.warning("Cannot update unknown RSS feed "
                                "{0}.".format(feed))
            return

        with (yield from self.updater[feed]["lock"]):
            self.logger.debug("Running update for RSS feed {0}.".format(feed))

            feed_url = RSS_FEEDS[feed]["url"]
            new_entry = yield from self.get_latest(feed_url)
            old_entry = self.updater[feed]["latest"]

            # remember latest entry
            self.updater[feed]["latest"] = new_entry
            self.updater[feed]["last"] = self.loop.time()

            if not old_entry:
                self.logger.info("Detected first entry for RSS feed "
                                 "{0}.".format(feed))
            elif old_entry["url"] != new_entry["url"]:
                self.logger.info("Detected new entry for RSS feed "
                                 "{0}.".format(feed))
                if announce:
                    yield from self.announce(feed)

    @asyncio.coroutine
    def announce(self, feed, *, target=None):
        if feed not in self.updater or feed not in RSS_FEEDS:
            self.logger.warning("Cannot announce unknown RSS feed "
                                "{0}.".format(feed))
            return

        entry = self.updater[feed]["latest"]
        if not entry:
            return

        entry_msg = "{0}: {1} ({2}) [{3}Z]".format(
            RSS_FEEDS[feed]["title"],
            entry["title"], entry["url"], entry["time"].isoformat())

        if target:
            yield from self.client.privmsg(target, entry_msg)
        else:
            yield from self.client.announce(entry_msg)

    @staticmethod
    @asyncio.coroutine
    def get_latest(feed_url):
        logger = logging.getLogger("lrrfeed")
        logger.debug("Retrieving latest entry for {0}.".format(feed_url))

        feed_req = yield from aiohttp.request(
            "get", feed_url, headers={"Accept": "application/rss+xml"})
        feed_body = yield from feed_req.text()
        feed = feedparser.parse(feed_body)
        if not feed.entries or not len(feed.entries):
            logger.warning(
                "RSS feed {0} did not provide any entries.".format(feed_url))

        latest = feed.entries[0]
        time = datetime.datetime(*latest.published_parsed[:6])

        return {"url": latest.id,
                "title": latest.title,
                "time": time}
