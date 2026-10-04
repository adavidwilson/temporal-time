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
    parts = text.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"time '{text}' is not in HH:MM format")
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"time '{text}' is not in HH:MM format"
        ) from None
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise argparse.ArgumentTypeError(
            f"time '{text}' is out of range (expected 00:00-23:59)"
        )
    return hours * 60 + minutes


def parse_temporal_time(text: str) -> int:
    """Parse a temporal 'H:MM' string (hour 1..12) into minutes."""
    parts = text.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"temporal time '{text}' is not in HH:MM format"
        )
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"temporal time '{text}' is not in HH:MM format"
        ) from None
    if not (1 <= hours <= 12 and 0 <= minutes < 60):
        raise argparse.ArgumentTypeError(
            "temporal hour must be 1..12 with minutes 00..59 "
            f"(got {hours}:{minutes:02d})"
        )
    return hours * 60 + minutes


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
    """Compute temporal time from times-in-minutes-since-midnight."""
    day_minutes = sunset - sunrise
    if day_minutes <= 0:
        day_minutes += MINUTES_PER_DAY  # daytime window crosses midnight
    night_minutes = MINUTES_PER_DAY - day_minutes

    # now / sunrise / sunset are minutes since 00:00 (0..1439).
    elapsed_day = (now - sunrise) % MINUTES_PER_DAY
    elapsed_night = (now - sunset) % MINUTES_PER_DAY

    if elapsed_day <= day_minutes:
        in_daytime = True
        elapsed = elapsed_day
        hour_len = day_minutes / 12.0
    elif elapsed_night <= night_minutes:
        in_daytime = False
        elapsed = elapsed_night
        hour_len = night_minutes / 12.0
    else:
        raise ValueError(
            "sunrise/sunset are inconsistent "
            "(sunset should be after sunrise within the ~24h cycle)"
        )

    # 0.0 .. 12.0 temporal hours elapsed since the start of the period.
    temporal_hour = elapsed / hour_len
    whole = int(temporal_hour)
    frac_minutes = (temporal_hour - whole) * 60.0
    # Hours are numbered 1..12: hour 1 starts at sunrise/sunset, hour 12 ends.
    current_hour = min(whole + 1, 12)

    return TemporalTime(
        in_daytime=in_daytime,
        hour_len=hour_len,
        temporal_hour=temporal_hour,
        whole_hour=whole,
        current_hour=current_hour,
        minutes=frac_minutes,
        day_minutes=day_minutes,
        night_minutes=night_minutes,
    )


def temporal_to_wall_clock(
    sunrise: int, sunset: int, temp_minutes: int, period: Literal["day", "night"]
) -> float:
    """Convert a temporal instant into equinoctial wall-clock minutes.

    A temporal time of (hour, minute) sits (hour - 1 + minute / 60) temporal
    hours after the start of its 12-hour block. Multiplying by that block's
    hour length gives the wall-clock minutes past sunrise (day) or sunset
    (night).
    """
    hours = temp_minutes // 60
    minutes = temp_minutes % 60
    if not (1 <= hours <= 12 and 0 <= minutes < 60):
        raise ValueError(f"temporal hour must be 1..12 (got {hours}:{minutes:02d})")

    day_minutes = sunset - sunrise
    if day_minutes <= 0:
        day_minutes += MINUTES_PER_DAY
    night_minutes = MINUTES_PER_DAY - day_minutes

    if period == "day":
        start = sunrise
        hour_len = day_minutes / 12.0
    else:  # period == "night"
        start = sunset
        hour_len = night_minutes / 12.0

    elapsed = ((hours - 1) + minutes / 60.0) * hour_len
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
    dur = human_duration
    day_len = result["day_minutes"]
    night_len = MINUTES_PER_DAY - day_len
    period = "daytime" if result["in_daytime"] else "nighttime"
    temporal_hour = result["temporal_hour"]
    whole_hour = result["current_hour"]
    minute = int(result["minutes"] + 0.5)
    if minute == 60:
        whole_hour += 1
        minute = 0
    wall = f"{args.now // 60:02d}:{args.now % 60:02d}"

    lines = [
        "Temporal (unequal) hour calculator",
        f"  Sunrise : {args.sunrise // 60:02d}:{args.sunrise % 60:02d}",
        f"  Sunset  : {args.sunset // 60:02d}:{args.sunset % 60:02d}",
        (
            f"  Day     : {dur(day_len)}   "
            f"1 temporal hour = {dur(day_len / 12.0)} ({day_len / 12.0:.1f} min)"
        ),
        (
            f"  Night   : {dur(night_len)}   "
            f"1 temporal hour = {dur(night_len / 12.0)} ({night_len / 12.0:.1f} min)"
        ),
        "",
        f"  Current wall-clock time : {wall}",
        f"  You are in {period.capitalize()}.",
        (
            f"  Temporal time : {whole_hour:02d}:{minute:02d}  "
            f"(hour {whole_hour} of {period}, {temporal_hour:.2f} elapsed)"
        ),
    ]

    if reverse_wall is not None:
        input_hours = args.temporal_time // 60
        input_minutes = args.temporal_time % 60
        reverse_hours = reverse_wall // 60
        reverse_minutes = reverse_wall % 60
        lines += [
            "",
            "Temporal -> equinoctial conversion",
            f"  Input        : {input_hours:02d}:{input_minutes:02d} ",
            f"({args.period} block)",
            f"  -> Equinoctial: {reverse_hours:02d}:{reverse_minutes:02d}",
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

    try:
        result = compute(args.sunrise, args.sunset, args.now)
    except ValueError as exc:
        parser_error(str(exc))

    reverse_wall: float | None = None
    if args.temporal_time is not None:
        try:
            reverse_wall = temporal_to_wall_clock(
                args.sunrise, args.sunset, args.temporal_time, args.period
            )
        except argparse.ArgumentTypeError as exc:
            parser_error(str(exc))

    print(format_output(args, result, reverse_wall))
    return 0


def parser_error(message: str) -> NoReturn:
    """Report an error through argparse and exit."""
    argparse.ArgumentParser().error(message)


if __name__ == "__main__":
    raise SystemExit(main())
