from datetime import timedelta
from math import floor

from pytimeparse.timeparse import timeparse


def parse_timeout(value: str, default: str = '30 secs') -> timedelta:
    return timedelta(seconds=timeparse(value or default))


def calc_next_interval(
    initial_period: timedelta,
    iteration: int,
    iteration_divisor: int = 1,
    max_seconds: float = 3600,
) -> float:
    """
    The function counts the next time interval in seconds with progressive increase

    initial_period: Initial value of the period.
    iteration: Current iteration number.
    iteration_divisor: Iteration divider, for the ability to change the interval
    not every iteration, but after several.
    max_seconds: Maximum period duration in seconds.
    """

    def calc_interval(initial: float, iterations: int) -> float:
        f = initial
        for i in range(iterations):
            f *= 2.0 if i % 2 == 0 else 1.5
        return f

    initial_period = initial_period.total_seconds()
    return min(calc_interval(initial_period, floor(iteration / iteration_divisor)), max_seconds)
