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
import functools
import logging
import protocol
import schedulrr
import signal

LOG_FORMAT = "{levelname}({name}): {message}"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, style="{")


def main():
    logger = logging.getLogger("pump19")
    logger.info("Pump19 started.")

    client_config = config.get_config("irc")
    client = protocol.Protocol(**client_config)
    loop = client.loop

    cmdhdl_config = config.get_config("cmd")
    cmdhdl = command.CommandHandler(client, loop=loop, **cmdhdl_config)

    logger.info("Starting 18 Games and Counting Scheduler")
    coro_18gac = functools.partial(
            cmdhdl.handle_command_18gac, None, None, count=4)
    sched_18gac = schedulrr.ScheduLRR(
            "*/10 * * * *", coro_18gac, loop)

    def shutdown():
        logger.info("Shutdown signal received.")
        sched_18gac.stop()
        client.shutdown()
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    logger.info("Running protocol activity.")
    client.start()
    sched_18gac.start()
    loop.run_forever()

    # before we stop the event loop, make sure all tasks are done
    pending = asyncio.Task.all_tasks(loop)
    if pending:
        loop.run_until_complete(asyncio.wait(pending, timeout=5))

    loop.close()
    logger.info("Protocol activity ceased.")
    logger.info("Exiting...")


if __name__ == "__main__":
    main()
