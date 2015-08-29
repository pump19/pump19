#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
pump19.py

The Pump19 IRC Golem entry point.
It sets up logging and starts up the IRC client.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""

import asyncio
import command
import config
import logging
import lrrfeed
import protocol
import signal
import songs

LOG_FORMAT = "{levelname}({name}): {message}"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, style="{")


def main():
    logger = logging.getLogger("pump19")
    logger.info("Pump19 started.")

    loop = asyncio.get_event_loop()
    client_config = config.get_config("irc")
    client = protocol.Protocol(**client_config)

    feed_config = config.get_config("rss")
    feed = lrrfeed.LRRFeedParser(client, **feed_config)
    feed.start()

    rdio_config = config.get_config("rdio")
    rdio_client = songs.Rdio(loop=loop, **rdio_config)

    cmdhdl_config = config.get_config("cmd")
    # we don't need to remember this instance
    command.CommandHandler(client, feed, rdio_client, **cmdhdl_config)

    def shutdown():
        logger.info("Shutdown signal received.")
        rdio_client.close()
        feed.stop()
        client.shutdown()
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    logger.info("Running protocol activity.")
    task = client.run()
    loop.run_until_complete(task)

    # before we stop the event loop, make sure all tasks are done
    pending = asyncio.Task.all_tasks(loop)
    if pending:
        loop.run_until_complete(asyncio.wait(pending, timeout=5))

    loop.close()
    logger.info("Protocol activity ceased.")
    logger.info("Exiting...")

if __name__ == "__main__":
    main()
