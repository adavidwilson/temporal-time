#!/usr/bin/env python3
"""Unit tests for :mod:`temporal_time`.

Run with either::

    python3 -m unittest -v
    python3 test_temporal_time.py
"""

import argparse
import unittest

from temporal_time import (
    MINUTES_PER_DAY,
    compute,
    current_wallclock_minutes,
    human_duration,
    parse_args,
    parse_temporal_time,
    parse_time,
    temporal_to_wall_clock,
)

SUNRISE = 6 * 60        # 06:00
SUNSET = 20 * 60 + 30   # 20:30


class ParseTimeTests(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(parse_time("06:00"), 6 * 60)
        self.assertEqual(parse_time("20:30"), SUNSET)
        self.assertEqual(parse_time("00:00"), 0)
        self.assertEqual(parse_time("23:59"), 23 * 60 + 59)

    def test_parse_time_rejects_out_of_range(self):
        for bad in ("24:00", "06:60", "25:00"):
            with self.assertRaises(argparse.ArgumentTypeError):
                parse_time(bad)

    def test_parse_temporal_time(self):
        self.assertEqual(parse_temporal_time("01:00"), 60)
        self.assertEqual(parse_temporal_time("12:00"), 12 * 60)
        self.assertEqual(parse_temporal_time("06:30"), 6 * 60 + 30)

    def test_parse_temporal_time_rejects_out_of_range(self):
        for bad in ("00:00", "13:00", "12:60"):
            with self.assertRaises(argparse.ArgumentTypeError):
                parse_temporal_time(bad)


class HumanDurationTests(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(human_duration(0), "0h 0m")
        self.assertEqual(human_duration(45), "0h 45m")

    def test_hours(self):
        self.assertEqual(human_duration(72), "1h 12m")
        self.assertEqual(human_duration(1080), "18h 0m")

    def test_rounding(self):
        self.assertEqual(human_duration(90), "1h 30m")
        self.assertEqual(human_duration(72.5), "1h 13m")
        self.assertEqual(human_duration(870), "14h 30m")


class ComputeTests(unittest.TestCase):
    def test_midday(self):
        result = compute(SUNRISE, SUNSET, 12 * 60)
        self.assertTrue(result["in_daytime"])
        self.assertEqual(result["day_minutes"], SUNSET - SUNRISE)
        self.assertEqual(
            result["night_minutes"], MINUTES_PER_DAY - (SUNSET - SUNRISE)
        )
        self.assertAlmostEqual(
            result["temporal_hour"], 6 * 60 / 72.5, places=3
        )
        self.assertEqual(result["current_hour"], 5)

    def test_start_of_day(self):
        result = compute(SUNRISE, SUNSET, SUNRISE)
        self.assertTrue(result["in_daytime"])
        self.assertAlmostEqual(result["temporal_hour"], 0.0, places=3)
        self.assertEqual(result["current_hour"], 1)

    def test_end_of_day(self):
        result = compute(SUNRISE, SUNSET, SUNSET - 1)
        self.assertTrue(result["in_daytime"])
        self.assertAlmostEqual(result["temporal_hour"], 12.0, places=1)
        self.assertEqual(result["current_hour"], 12)

    def test_midnight_is_night(self):
        result = compute(SUNRISE, SUNSET, 0)
        self.assertFalse(result["in_daytime"])
        self.assertAlmostEqual(result["temporal_hour"], 210 / 47.5, places=3)

    def test_day_crosses_midnight(self):
        # sunrise after sunset means the daytime window wraps past midnight.
        result = compute(SUNSET, SUNRISE, 12 * 60)
        self.assertEqual(
            result["day_minutes"], MINUTES_PER_DAY - (SUNSET - SUNRISE)
        )


class TemporalToWallClockTests(unittest.TestCase):
    def test_first_hour_of_day_is_sunrise(self):
        self.assertEqual(
            temporal_to_wall_clock(SUNRISE, SUNSET, 60, "day"), SUNRISE
        )

    def test_first_hour_of_night_is_sunset(self):
        self.assertEqual(
            temporal_to_wall_clock(SUNRISE, SUNSET, 60, "night"), SUNSET
        )

    def test_mid_hour_of_day(self):
        got = temporal_to_wall_clock(SUNRISE, SUNSET, 6 * 60, "day")
        self.assertAlmostEqual(got, 722.5, places=1)

    def test_mid_hour_of_night(self):
        got = temporal_to_wall_clock(SUNRISE, SUNSET, 6 * 60, "night")
        expected = (SUNSET + 5 * (MINUTES_PER_DAY - (SUNSET - SUNRISE)) / 12) \
            % MINUTES_PER_DAY
        self.assertAlmostEqual(got, expected, places=1)

    def test_rejects_bad_temporal_hour(self):
        with self.assertRaises(ValueError):
            temporal_to_wall_clock(SUNRISE, SUNSET, 0, "day")
        with self.assertRaises(ValueError):
            temporal_to_wall_clock(SUNRISE, SUNSET, 13 * 60, "day")


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self):
        args = parse_args(["--sunrise", "06:00", "--sunset", "20:30"])
        self.assertEqual(args.sunrise, 6 * 60)
        self.assertEqual(args.sunset, 20 * 60 + 30)
        self.assertIsNone(args.now)
        self.assertIsNone(args.temporal_time)
        self.assertEqual(args.period, "day")

    def test_full_args(self):
        args = parse_args([
            "--sunrise", "06:00",
            "--sunset", "20:30",
            "--now", "14:00",
            "--temporal-time", "01:00",
            "--period", "night",
        ])
        self.assertEqual(args.now, 14 * 60)
        self.assertEqual(args.temporal_time, 60)
        self.assertEqual(args.period, "night")


class CurrentWallclockTests(unittest.TestCase):
    def test_within_range(self):
        minutes = current_wallclock_minutes()
        self.assertTrue(0 <= minutes < MINUTES_PER_DAY)


if __name__ == "__main__":
    unittest.main()
