"""Custom SQLAlchemy column types."""
from __future__ import annotations

import enum
from typing import Type

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class EnumType(TypeDecorator):
    """Stores a Python ``str`` enum as its value and restores it as the enum.

    Using a plain ``String`` column with ``Mapped[SomeEnum]`` does not convert
    values back to the enum on load; this decorator makes the round-trip clean.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: Type[enum.Enum], length: int = 50, **kw):
        self.enum_cls = enum_cls
        super().__init__(length=length, **kw)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_cls):
            return value.value
        return self.enum_cls(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_cls(value)
