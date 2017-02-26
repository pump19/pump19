#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
schedulrr.py

Asynchronous scheduler based on MoonBaseTime.
Controls recurring events for Pump19.

Copyright (c) 2017 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

from croniter import croniter
from datetime import datetime, timedelta
from dateutil.tz import gettz

import asyncio
import logging

MoonBaseTime = gettz("Canada/Pacific")
EPS_DELAY = timedelta(seconds=1)
MAX_DELAY = timedelta(hours=1)


class ScheduLRR:
    """
    ScheduLRR manages a recurring tasks.
    """
    logger = logging.getLogger("schedulrr")

    def __init__(self, crontab, coro, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.task = None

        base_time = datetime.now(tz=MoonBaseTime)
        self.cron = croniter(crontab, base_time, datetime)
        self.coro = coro

        self.logger.info(f"Created new ScheduLRR with crontab {crontab!s}.")

    async def run(self):
        while True:  # we're fine with not handling a CancelledError
            now = datetime.now(tz=MoonBaseTime)
            nxt = self.cron.get_current()
            diff = nxt - now
            if diff <= EPS_DELAY:
                await self.coro()
                nxt = self.cron.get_next()
                self.logger.debug(f"Next action scheduled for {nxt!s}.")
            else:
                delay = MAX_DELAY if diff >= MAX_DELAY else diff
                await asyncio.sleep(delay.total_seconds())

    def start(self):
        if self.task:
            self.logger.warning("Task already active...")

        # initialize croniter
        nxt = self.cron.get_next()
        self.logger.debug(f"Next action scheduled for {nxt!s}.")

        self.task = self.loop.create_task(self.run())

    def stop(self):
        if not self.task:
            return

        self.task.cancel()
        self.task = None
