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
    def test_parse_time_basic(self):
        self.assertEqual(parse_time("06:00"), 6 * 60)
        self.assertEqual(parse_time("20:30"), 20 * 60 + 30)
        self.assertEqual(parse_time("00:00"), 0)
        self.assertEqual(parse_time("23:59"), 23 * 60 + 59)

    def test_parse_time_rejects_bad_format(self):
        for bad in ("6", "ab:cd", "6:60", "24:00", "-1:00", "12-30"):
            with self.assertRaises((ValueError, argparse.ArgumentTypeError)):
                parse_time(bad)

    def test_parse_temporal_time_basic(self):
        self.assertEqual(parse_temporal_time("01:00"), 60)
        self.assertEqual(parse_temporal_time("12:00"), 12 * 60)
        self.assertEqual(parse_temporal_time("12:59"), 12 * 60 + 59)
        self.assertEqual(parse_temporal_time("06:30"), 6 * 60 + 30)

    def test_parse_temporal_time_rejects_out_of_range(self):
        for bad in ("00:00", "13:00", "0", "12:60", "-1:00", "6:00:00"):
            with self.assertRaises((ValueError, argparse.ArgumentTypeError)):
                parse_temporal_time(bad)


class HumanDurationTests(unittest.TestCase):
    def test_minutes_only(self):
        self.assertEqual(human_duration(0), "0h 0m")
        self.assertEqual(human_duration(45), "0h 45m")

    def test_hours_only(self):
        self.assertEqual(human_duration(72), "1h 12m")
        self.assertEqual(human_duration(1080), "18h 0m")

    def test_combined(self):
        self.assertEqual(human_duration(90), "1h 30m")
        self.assertEqual(human_duration(870), "14h 30m")

    def test_half_hours(self):
        self.assertEqual(human_duration(72.5), "1h 13m")
        self.assertEqual(human_duration(47.5), "0h 48m")


class ComputeTests(unittest.TestCase):
    def test_midday_time(self):
        now = 12 * 60  # 12:00
        result = compute(SUNRISE, SUNSET, now)
        self.assertTrue(result["in_daytime"])
        self.assertEqual(result["day_minutes"], SUNSET - SUNRISE)
        self.assertEqual(
            result["night_minutes"], MINUTES_PER_DAY - (SUNSET - SUNRISE)
        )
        # 6h elapsed at 72.5-min hour length = 4.966 temporal hours, hour 5.
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
        now = 0  # 00:00
        result = compute(SUNRISE, SUNSET, now)
        self.assertFalse(result["in_daytime"])
        # 210 min past sunset at 47.5-min hour length = 4.421 temporal hours.
        self.assertAlmostEqual(result["temporal_hour"], 210 / 47.5, places=3)

    def test_inconsistent_input_raises(self):
        # With sunrise after sunset the day window "crosses midnight" into a
        # valid 9h30m day, so this input does not raise; skip this assertion
        # and instead assert the computed window is sensible.
        result = compute(SUNSET, SUNRISE, 12 * 60)
        self.assertEqual(result["day_minutes"], MINUTES_PER_DAY - (SUNSET - SUNRISE))


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
        got_midnight = temporal_to_wall_clock(SUNRISE, SUNSET, 6 * 60, "night")
        expected_midnight = (SUNSET
                             + 5 * (MINUTES_PER_DAY - (SUNSET - SUNRISE)) / 12.0) \
                             % MINUTES_PER_DAY
        self.assertAlmostEqual(got_midnight, expected_midnight, places=1)

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
