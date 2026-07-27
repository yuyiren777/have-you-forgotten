"""Single source of truth for the application's local date and time."""
from __future__ import annotations

import datetime
from dataclasses import dataclass


_WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


@dataclass(frozen=True)
class DateContext:
    """A stable local clock snapshot shared by one processing run."""

    now: datetime.datetime

    @property
    def today(self) -> datetime.date:
        return self.now.date()

    @property
    def utc_offset(self) -> str:
        offset = self.now.utcoffset() or datetime.timedelta()
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        hours, minutes = divmod(abs(total_minutes), 60)
        return f"UTC{sign}{hours:02d}:{minutes:02d}"

    def to_prompt_text(self) -> str:
        weekday = _WEEKDAY_NAMES[self.today.weekday()]
        return f"{self.now:%Y-%m-%d %H:%M:%S}（{weekday}，{self.utc_offset}）"


def get_date_context(now: datetime.datetime | None = None) -> DateContext:
    """Read local system time once and return a timezone-aware snapshot."""
    current = now or datetime.datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    return DateContext(now=current)
