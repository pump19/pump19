#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

import asyncio


def main():
    loop = asyncio.get_event_loop()
    loop.run_forever()

if __name__ == "__main__":
    main()
