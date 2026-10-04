#!/usr/bin/env python3
"""Compute the current time in temporal (unequal) hours.

Temporal hours divide daytime (sunrise -> sunset) into 12 equal parts and
nighttime (sunset -> sunrise) into a separate 12 equal parts, so each temporal
hour changes length with the seasons. Unlike 24-hour time, daytime and
nighttime hours are not the same length. Usage:

    python3 temporal_time.py --sunrise 06:00 --sunset 20:30

Pass --now HH:MM to override the system's current wall-clock time (useful for
testing or computing a fixed moment).
"""

import argparse
import datetime


def parse_temporal_time(text):
    """Parse a temporal 'H:MM' or 'HH:MM' string (hour 1..12) into minutes."""
    try:
        h, m = text.split(":")
        h, m = int(h), int(m)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"temporal time '{text}' is not in HH:MM format"
        )
    if not (1 <= h <= 12 and 0 <= m < 60):
        raise argparse.ArgumentTypeError(
            "temporal hour must be 1..12 with minutes 00..59 (got "
            f"{h}:{m:02d})"
        )
    return h * 60 + m


def parse_time(text):
    """Parse an 'HH:MM' string into minutes since 00:00."""
    try:
        h, m = text.split(":")
        h, m = int(h), int(m)
    except ValueError:
        raise argparse.ArgumentTypeError(f"time '{text}' is not in HH:MM format")
    if not (0 <= h < 24 and 0 <= m < 60):
        raise argparse.ArgumentTypeError(
            f"time '{text}' is out of range (expected 00:00-23:59)"
        )
    return h * 60 + m


def human_duration(minutes):
    """Format a duration in minutes as 'Xh Ym'."""
    h = int(minutes // 60)
    m = int(round(minutes % 60))
    if m == 60:  # rounds up a minute that rounded to a full extra hour
        h += 1
        m = 0
    return f"{h}h {m}m"


def compute(sunrise, sunset, now):
    """Compute temporal time from times-in-minutes-since-midnight."""
    day_minutes = sunset - sunrise
    if day_minutes <= 0:  # daytime window crosses midnight
        day_minutes += 24 * 60
    night_minutes = (24 * 60) - day_minutes

    # now / sunrise / sunset are minutes since 00:00 (0..1439).
    elapsed_day = (now - sunrise) % (24 * 60)
    elapsed_night = (now - sunset) % (24 * 60)

    if elapsed_day <= day_minutes:
        in_daytime = True
        elapsed = elapsed_day
        hour_len = day_minutes / 12.0
    elif elapsed_night <= night_minutes:
        in_daytime = False
        elapsed = elapsed_night
        hour_len = night_minutes / 12.0
    else:  # should not happen, but avoids a crash on bad input
        raise ValueError(
            "sunrise/sunset are inconsistent "
            "(sunset should be after sunrise within the ~24h cycle)"
        )

    temporal_hour = elapsed / hour_len  # 0.0 .. 12.0
    whole = int(temporal_hour)
    frac_minutes = (temporal_hour - whole) * 60.0
    # Hours are numbered 1..12: hour 1 starts at sunrise/sunset, hour 12 ends.
    current_hour = min(whole + 1, 12)

    return {
        "in_daytime": in_daytime,
        "hour_len": hour_len,
        "temporal_hour": temporal_hour,
        "whole_hour": whole,
        "current_hour": current_hour,
        "minutes": frac_minutes,
        "day_minutes": day_minutes,
        "night_minutes": night_minutes,
    }


def temporal_to_wall_clock(sunrise, sunset, temp_minutes, period):
    """Convert a temporal instant back into equinoctial wall-clock minutes.

    A temporal time of (hour, minute) sits (hour-1 + minute/60) temporal-hours
    after the start of its 12-hour block. Multiply by that block's hour length
    to get elapsed wall-clock minutes from sunrise (day) or sunset (night).
    """
    h, m = temp_minutes // 60, temp_minutes % 60
    if not (1 <= h <= 12 and 0 <= m < 60):
        raise argparse.ArgumentTypeError(
            f"temporal hour must be 1..12 (got {h}:{m:02d})"
        )
    day_minutes = sunset - sunrise
    if day_minutes <= 0:
        day_minutes += 24 * 60
    night_minutes = (24 * 60) - day_minutes

    if period == "day":
        start, hour_len = sunrise, day_minutes / 12.0
    elif period == "night":
        start, hour_len = sunset, night_minutes / 12.0
    else:
        raise argparse.ArgumentTypeError("period must be 'day' or 'night'")

    frac = (h - 1) + m / 60.0  # hour 1 begins at 0 elapsed
    elapsed = frac * hour_len
    wall = (start + elapsed) % (24 * 60)
    return wall


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute the current time in temporal (unequal) hours."
    )
    parser.add_argument("--sunrise", required=True, type=parse_time,
                        help="Sunrise as HH:MM (00:00-23:59)")
    parser.add_argument("--sunset", required=True, type=parse_time,
                        help="Sunset as HH:MM (00:00-23:59)")
    parser.add_argument("--now", type=parse_time, default=None,
                        help="Current wall-clock time as HH:MM. "
                             "Defaults to the system's current time.")
    parser.add_argument(
        "--temporal-time", type=parse_temporal_time, default=None,
        help="A temporal time (hour 1..12) to convert back into equinoctial "
             "wall-clock time, e.g. --temporal-time 01:00.",
    )
    parser.add_argument(
        "--period", choices=["day", "night"], default="day",
        help="Which 12-hour block --temporal-time refers to (default: day). "
             "Needed when the temporal time is ambiguous between day and night.",
    )
    args = parser.parse_args(argv)

    now = args.now
    if now is None:
        now = (datetime.datetime.now().time().hour * 60
               + datetime.datetime.now().time().minute)

    try:
        result = compute(args.sunrise, args.sunset, now)
    except ValueError as exc:
        parser.error(str(exc))

    reverse_wall = None
    if args.temporal_time is not None:
        try:
            reverse_wall = temporal_to_wall_clock(
                args.sunrise, args.sunset, args.temporal_time, args.period
            )
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))

    dur = human_duration
    day_len = result["day_minutes"]
    night_len = 24 * 60 - day_len
    period = "daytime" if result["in_daytime"] else "nighttime"
    temporal_hour = result["temporal_hour"]
    whole_hour = result["current_hour"]
    minute = int(round(result["minutes"]))

    wall = f"{now // 60:02d}:{now % 60:02d}"
    print("Temporal (unequal) hour calculator")
    print(f"  Sunrise : {args.sunrise // 60:02d}:{args.sunrise % 60:02d}")
    print(f"  Sunset  : {args.sunset // 60:02d}:{args.sunset % 60:02d}")
    print(f"  Day     : {dur(day_len)}   "
          f"1 temporal hour = {dur(day_len / 12.0)} ({day_len / 12.0:.1f} min)")
    print(f"  Night   : {dur(night_len)}   "
          f"1 temporal hour = {dur(night_len / 12.0)} ({night_len / 12.0:.1f} min)")
    print()
    print(f"  Current wall-clock time : {wall}")
    print(f"  You are in {period.capitalize()}.")
    print(f"  Temporal time : "
          f"{whole_hour:02d}:{minute:02d}  "
          f"(hour {whole_hour} of {period}, {temporal_hour:.2f} elapsed)")

    if reverse_wall is not None:
        th = args.temporal_time // 60
        tm = args.temporal_time % 60
        rh, rm = int(reverse_wall // 60), int(reverse_wall % 60)
        print(f"  Input        : {th:02d}:{tm:02d} ({args.period} block)")
        print(f"  -> Equinoctial: {rh:02d}:{rm:02d}")


if __name__ == "__main__":
    main()
