from datetime import timedelta

import strawberry
from pytimeparse.timeparse import timeparse

TimeDelta = strawberry.scalar(
    timedelta, serialize=lambda v: str(v), parse_value=lambda v: timedelta(seconds=timeparse(v))
)
