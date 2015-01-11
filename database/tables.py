#!/usr/bin/env python3
# vim:fileencoding=utf-8:ts=8:et:sw=4:sts=4:tw=79

"""
tables.py

Table definitions for pearbot database submodule.
Tables are not assigned to variables, they can be accessed using the global
metadata object though.

Copyright (c) 2015 Twisted Pear <pear at twistedpear dot at>
See the file LICENSE for copying permission.
"""

from sqlalchemy import MetaData, Table, Column, Integer, String

METADATA = MetaData()

Table("quote", METADATA,
      Column("qid", Integer, primary_key=True),
      Column("text", String, nullable=False))

Table("moderator", METADATA,
      Column("stream", String, primary_key=True),
      Column("name", String, primary_key=True))
