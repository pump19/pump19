#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
pearbot.py

The PearBot IRC bot entry point.
It sets up logging and starts up the IRC client.

Copyright (c) 2014 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

import asyncio
import config
import logging
import protocol
import signal

LOG_FORMAT = "%(asctime)-15s %(name)-10s %(levelname)-8s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main():
    logger = logging.getLogger("pearbot")
    logger.info("PearBot started.")

    loop = asyncio.get_event_loop()
    client_config = config.get_config("irc")
    client = protocol.Protocol(**client_config)

    def shutdown():
        logger.info("Shutdown signal received.")
        client.shutdown()
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    logger.info("Running protocol activity.")
    task = client.run()
    loop.run_until_complete(task)
    logger.info("Protocol activity ceased.")
    logger.info("Exiting...")

if __name__ == "__main__":
    main()
