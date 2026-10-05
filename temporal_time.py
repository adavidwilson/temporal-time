#!/usr/bin/env python3
"""Compute the current time in temporal (unequal) hours.

Temporal hours divide daytime (sunrise -> sunset) into 12 equal parts and
nighttime (sunset -> sunrise) into a separate 12 equal parts, so each temporal
hour changes length with the seasons. Unlike 24-hour time, daytime and
nighttime hours are not the same length. Usage:

    python3 temporal_time.py --sunrise 06:00 --sunset 20:30

Pass --now HH:MM to override the system's current wall-clock time (useful for
testing or computing a fixed moment).

Use --temporal-time HH:MM to convert a temporal instant back into the
equinoctial (24-hour) wall-clock time it corresponds to.
"""

from __future__ import annotations

import argparse
import datetime
from typing import Literal, NoReturn, TypedDict

MINUTES_PER_DAY = 24 * 60


def parse_time(text: str) -> int:
    """Parse an 'HH:MM' wall-clock string into minutes since 00:00."""
    hour_str, minute_str = text.split(":")
    hour, minute = int(hour_str), int(minute_str)
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a valid time (expected 00:00-23:59)"
        )
    return hour * 60 + minute


def parse_temporal_time(text: str) -> int:
    """Parse a temporal 'H:MM' string (hour 1..12) into minutes."""
    hour_str, minute_str = text.split(":")
    hour, minute = int(hour_str), int(minute_str)
    if not (1 <= hour <= 12 and 0 <= minute < 60):
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a valid temporal time (hour must be 1..12)"
        )
    return hour * 60 + minute


def human_duration(minutes: float) -> str:
    """Format a duration in minutes as 'Xh Ym' (rounding half-up)."""
    hours = int(minutes // 60)
    leftover = int(minutes % 60 + 0.5)
    if leftover == 60:
        hours += 1
        leftover = 0
    return f"{hours}h {leftover}m"


class TemporalTime(TypedDict):
    """Fields returned by :func:`compute`."""

    in_daytime: bool
    hour_len: float
    temporal_hour: float
    whole_hour: int
    current_hour: int
    minutes: float
    day_minutes: int
    night_minutes: int


def compute(sunrise: int, sunset: int, now: int) -> TemporalTime:
    """Compute the temporal time for ``now`` given sunrise/sunset times."""
    day_minutes = sunset - sunrise
    if day_minutes <= 0:
        day_minutes += MINUTES_PER_DAY  # daytime crosses midnight
    night_minutes = MINUTES_PER_DAY - day_minutes

    elapsed_day = (now - sunrise) % MINUTES_PER_DAY
    elapsed_night = (now - sunset) % MINUTES_PER_DAY

    if elapsed_day <= day_minutes:
        in_daytime, elapsed, hour_len = True, elapsed_day, day_minutes / 12
    elif elapsed_night <= night_minutes:
        in_daytime, elapsed, hour_len = False, elapsed_night, night_minutes / 12
    else:
        raise ValueError(
            "sunrise/sunset are inconsistent "
            "(sunset should be after sunrise within the ~24h cycle)"
        )

    temporal_hour = elapsed / hour_len
    whole_hour = int(temporal_hour)
    minutes = (temporal_hour - whole_hour) * 60
    current_hour = min(whole_hour + 1, 12)  # hours are numbered 1..12

    return TemporalTime(
        in_daytime=in_daytime,
        hour_len=hour_len,
        temporal_hour=temporal_hour,
        whole_hour=whole_hour,
        current_hour=current_hour,
        minutes=minutes,
        day_minutes=day_minutes,
        night_minutes=night_minutes,
    )


def temporal_to_wall_clock(
    sunrise: int, sunset: int, temp_minutes: int, period: Literal["day", "night"]
) -> float:
    """Convert a temporal instant into wall-clock minutes since 00:00."""
    hour = temp_minutes // 60
    minute = temp_minutes % 60
    if not (1 <= hour <= 12 and 0 <= minute < 60):
        raise ValueError(f"'{hour}:{minute:02d}' is not a valid temporal time")

    day_minutes = sunset - sunrise
    if day_minutes <= 0:
        day_minutes += MINUTES_PER_DAY  # daytime crosses midnight
    night_minutes = MINUTES_PER_DAY - day_minutes

    if period == "day":
        start, hour_len = sunrise, day_minutes / 12
    else:
        start, hour_len = sunset, night_minutes / 12

    elapsed = ((hour - 1) + minute / 60) * hour_len
    return (start + elapsed) % MINUTES_PER_DAY


def current_wallclock_minutes() -> int:
    """Return the current wall-clock time in minutes since 00:00."""
    now = datetime.datetime.now().astimezone().time()
    return now.hour * 60 + now.minute


def format_output(
    args: argparse.Namespace,
    result: TemporalTime,
    reverse_wall: float | None,
) -> str:
    """Render the calculator result as a multi-line string."""
    day_minutes = result["day_minutes"]
    night_minutes = MINUTES_PER_DAY - day_minutes
    period = "daytime" if result["in_daytime"] else "nighttime"

    whole_hour = result["current_hour"]
    minute = int(result["minutes"] + 0.5)
    if minute == 60:  # rounding pushed us into the next hour
        whole_hour += 1
        minute = 0

    def hhmm(minutes: float) -> str:
        minutes = int(minutes)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    lines = [
        "Temporal (unequal) hour calculator",
        f"  Sunrise : {hhmm(args.sunrise)}",
        f"  Sunset  : {hhmm(args.sunset)}",
        (
            f"  Day     : {human_duration(day_minutes)}   "
            f"1 temporal hour = {human_duration(day_minutes / 12)} "
            f"({day_minutes / 12:.1f} min)"
        ),
        (
            f"  Night   : {human_duration(night_minutes)}   "
            f"1 temporal hour = {human_duration(night_minutes / 12)} "
            f"({night_minutes / 12:.1f} min)"
        ),
        "",
        f"  Current wall-clock time : {hhmm(args.now)}",
        f"  You are in {period.capitalize()}.",
        (
            f"  Temporal time : {whole_hour:02d}:{minute:02d}  "
            f"(hour {whole_hour} of {period}, {result['temporal_hour']:.2f} elapsed)"
        ),
    ]

    if reverse_wall is not None:
        lines += [
            "",
            "Temporal -> equinoctial conversion",
            (f"  Input        : {hhmm(args.temporal_time)} ({args.period} block)"),
            f"  -> Equinoctial: {hhmm(reverse_wall)}",
        ]

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute the current time in temporal (unequal) hours."
    )
    parser.add_argument(
        "--sunrise",
        required=True,
        type=parse_time,
        help="Sunrise as HH:MM (00:00-23:59)",
    )
    parser.add_argument(
        "--sunset",
        required=True,
        type=parse_time,
        help="Sunset as HH:MM (00:00-23:59)",
    )
    parser.add_argument(
        "--now",
        type=parse_time,
        default=None,
        help="Current wall-clock time as HH:MM. Defaults to the system's current time.",
    )
    parser.add_argument(
        "--temporal-time",
        type=parse_temporal_time,
        default=None,
        help="A temporal time (hour 1..12) to convert back into equinoctial "
        "wall-clock time, e.g. --temporal-time 01:00.",
    )
    parser.add_argument(
        "--period",
        choices=["day", "night"],
        default="day",
        help="Which 12-hour block --temporal-time refers to (default: day). "
        "Needed when the temporal time is ambiguous between day and night.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.now is None:
        args.now = current_wallclock_minutes()

    result = compute(args.sunrise, args.sunset, args.now)

    reverse_wall = None
    if args.temporal_time is not None:
        reverse_wall = temporal_to_wall_clock(
            args.sunrise, args.sunset, args.temporal_time, args.period
        )

    print(format_output(args, result, reverse_wall))
    return 0


def parser_error(message: str) -> NoReturn:
    """Report an error through argparse and exit."""
    argparse.ArgumentParser().error(message)


if __name__ == "__main__":
    raise SystemExit(main())
