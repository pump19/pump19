#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

from asyncio import coroutine
from struct import pack

"""
protocol.py

A subset of the current Minecraft protocol.

Copyright (c) 2015 Twisted Pear <tp at pump19 dot eu>
See the file LICENSE for copying permission.
"""


def pack_varint(value):
    packet = bytearray()
    for _ in range(5):
        if value & ~0x7F == 0:
            packet += pack("B", value)
            break
        else:
            packet += pack("B", value & 0x7F | 0x80)
            value >>= 7
    return bytes(packet)


@coroutine
def unpack_varint(stream):
    result = 0
    for i in range(5):
        part = yield from stream.read(1)
        part = ord(part)
        result |= (part & 0x7F) << (7 * i)
        if not part & 0x80:
            return result
    raise IOError("Could not parse data as VarInt.")


def pack_string(value):
    packet = bytearray()
    payload = value.encode()
    packet += pack_varint(len(payload))
    packet += payload
    return bytes(packet)


@coroutine
def unpack_string(stream):
    length = yield from unpack_varint(stream)
    raw = yield from stream.readexactly(length)
    return raw.decode()


def handshake(hostname, port, protocol=47):
    payload = bytearray()
    payload += pack_varint(0)  # packet ID
    payload += pack_varint(protocol)
    payload += pack_string(hostname)
    payload += pack(">H", port)
    payload += pack_varint(1)  # next state = Status

    packet = bytearray()
    packet += pack_varint(len(payload))
    packet += payload
    return bytes(packet)


def status_request():
    payload = bytearray()
    payload += pack_varint(0)  # packet ID

    packet = bytearray()
    packet += pack_varint(len(payload))
    packet += payload
    return bytes(packet)
